from __future__ import annotations

import copy
import json
import re
import time
from collections.abc import Iterator

from hz_bank_rag.core.config import settings
from hz_bank_rag.core.siliconflow_client import SiliconFlowClient, SiliconFlowError
from hz_bank_rag.retrieval.hybrid_retriever import HybridRetriever
from hz_bank_rag.retrieval.query_rewrite import QueryRewriter
from hz_bank_rag.retrieval.reranker import SiliconFlowReranker
from hz_bank_rag.service.query_cache import QueryCache
from hz_bank_rag.storage.metadata_store import MetadataStore
from hz_bank_rag.storage.rag_repository import RAGRepository


class QAService:
    """问答编排服务：把“检索 -> 生成 -> 记忆 -> 缓存”串成一个对外能力。"""

    def __init__(
        self,
        repo: RAGRepository,
        retriever: HybridRetriever,
        rewriter: QueryRewriter,
        reranker: SiliconFlowReranker,
        meta: MetadataStore,
    ) -> None:
        self.repo = repo
        self.retriever = retriever
        self.rewriter = rewriter
        self.reranker = reranker
        self.meta = meta
        self.llm_client = SiliconFlowClient()
        self.cache = (
            QueryCache(ttl_seconds=settings.query_cache_ttl_seconds, max_size=settings.query_cache_max_size)
            if settings.enable_query_cache
            else None
        )

    def ask(
        self,
        kb_id: str,
        query: str,
        top_k: int = 5,
        candidate_multiplier: int = 4,
        fast_mode: bool = True,
        session_id: str = "",
        use_memory: bool = True,
        refresh_cache: bool = False,
        retrieval_scope: str = "active_only",
        freshness_weight: float | None = None,
        dedup_by_family: bool | None = None,
    ) -> dict:
        # 主流程（同步版）：
        # 1) 查询改写 2) 命中缓存则直接返回
        # 3) 检索命中文档块 4) 组装上下文并调用大模型生成答案
        # 5) 保存会话记忆 6) 写入缓存
        start = time.perf_counter()
        rewritten = query if fast_mode else self.rewriter.rewrite(query)
        final_scope = retrieval_scope or settings.default_retrieval_scope
        final_freshness = settings.default_freshness_weight if freshness_weight is None else float(freshness_weight)
        final_dedup = settings.default_dedup_by_family if dedup_by_family is None else bool(dedup_by_family)
        cache_key = self._make_cache_key(
            kb_id=kb_id,
            query=query,
            rewritten=rewritten,
            top_k=top_k,
            candidate_multiplier=candidate_multiplier,
            fast_mode=fast_mode,
            session_id=session_id,
            use_memory=use_memory,
            retrieval_scope=final_scope,
            freshness_weight=final_freshness,
            dedup_by_family=final_dedup,
        )

        if self.cache is not None and not refresh_cache:
            # 命中缓存：省去检索和大模型调用，显著降低延迟与成本。
            cached = self.cache.get(cache_key)
            if cached is not None:
                result = copy.deepcopy(cached)
                result["cache_hit"] = True
                result["latency_ms"] = int((time.perf_counter() - start) * 1000)
                result["cache_stats"] = self.cache.stats()
                return result

        chunk_map = self.repo.get_kb_chunk_map(kb_id=kb_id, retrieval_scope=final_scope)
        if not chunk_map:
            # 新手常见问题：知识库为空时不是报错，而是返回可读提示。
            return {
                "kb_id": kb_id,
                "query": query,
                "rewritten_query": rewritten,
                "answer": "Knowledge base is empty. Please ingest documents first.",
                "citations": [],
                "cache_hit": False,
                "latency_ms": int((time.perf_counter() - start) * 1000),
            }

        hits = self._retrieve_hits(
            kb_id=kb_id,
            query=query,
            rewritten=rewritten,
            chunk_map=chunk_map,
            top_k=top_k,
            candidate_multiplier=candidate_multiplier,
            fast_mode=fast_mode,
            retrieval_scope=final_scope,
            freshness_weight=final_freshness,
            dedup_by_family=final_dedup,
        )

        memory_context, memory_meta = self._build_memory_context(kb_id=kb_id, session_id=session_id, use_memory=use_memory)
        answer = self._generate_answer(query=query, rewritten=rewritten, hits=hits, memory_context=memory_context)

        if session_id and use_memory:
            self._save_conversation_turn(session_id=session_id, kb_id=kb_id, query=query, answer=answer)

        result = {
            "kb_id": kb_id,
            "query": query,
            "rewritten_query": rewritten,
            "answer": answer,
            "fast_mode": fast_mode,
            "retrieval_scope": final_scope,
            "freshness_weight": final_freshness,
            "dedup_by_family": final_dedup,
            "session_id": session_id,
            "memory": memory_meta,
            "citations": [self._citation_from_hit(hit) for hit in hits],
            "cache_hit": False,
            "latency_ms": int((time.perf_counter() - start) * 1000),
        }

        if self.cache is not None:
            self.cache.set(cache_key, copy.deepcopy(result))
            result["cache_stats"] = self.cache.stats()
        return result

    def ask_stream(
        self,
        kb_id: str,
        query: str,
        top_k: int = 5,
        candidate_multiplier: int = 4,
        fast_mode: bool = True,
        session_id: str = "",
        use_memory: bool = True,
        retrieval_scope: str = "active_only",
        freshness_weight: float | None = None,
        dedup_by_family: bool | None = None,
    ) -> tuple[dict, Iterator[str]]:
        # 与 ask 逻辑基本一致，差异在于返回 token 迭代器，供 SSE 流式输出。
        rewritten = query if fast_mode else self.rewriter.rewrite(query)
        final_scope = retrieval_scope or settings.default_retrieval_scope
        final_freshness = settings.default_freshness_weight if freshness_weight is None else float(freshness_weight)
        final_dedup = settings.default_dedup_by_family if dedup_by_family is None else bool(dedup_by_family)
        chunk_map = self.repo.get_kb_chunk_map(kb_id=kb_id, retrieval_scope=final_scope)
        if not chunk_map:
            meta = {
                "kb_id": kb_id,
                "query": query,
                "rewritten_query": rewritten,
                "fast_mode": fast_mode,
                "citations": [],
                "session_id": session_id,
                "retrieval_scope": final_scope,
                "freshness_weight": final_freshness,
                "dedup_by_family": final_dedup,
            }

            def empty_stream() -> Iterator[str]:
                yield "Knowledge base is empty. Please ingest documents first."

            return meta, empty_stream()

        hits = self._retrieve_hits(
            kb_id=kb_id,
            query=query,
            rewritten=rewritten,
            chunk_map=chunk_map,
            top_k=top_k,
            candidate_multiplier=candidate_multiplier,
            fast_mode=fast_mode,
            retrieval_scope=final_scope,
            freshness_weight=final_freshness,
            dedup_by_family=final_dedup,
        )
        memory_context, memory_meta = self._build_memory_context(kb_id=kb_id, session_id=session_id, use_memory=use_memory)

        meta = {
            "kb_id": kb_id,
            "query": query,
            "rewritten_query": rewritten,
            "fast_mode": fast_mode,
            "retrieval_scope": final_scope,
            "freshness_weight": final_freshness,
            "dedup_by_family": final_dedup,
            "session_id": session_id,
            "memory": memory_meta,
            "citations": [self._citation_from_hit(hit) for hit in hits],
        }

        def stream_wrapper() -> Iterator[str]:
            chunks = []
            for token in self._generate_answer_stream(query=query, rewritten=rewritten, hits=hits, memory_context=memory_context):
                chunks.append(token)
                yield token
            if session_id and use_memory:
                self._save_conversation_turn(session_id=session_id, kb_id=kb_id, query=query, answer="".join(chunks))

        return meta, stream_wrapper()

    def build_retrieval_snapshot(
        self,
        kb_id: str,
        query: str,
        rewritten_query: str = "",
        top_k: int = 5,
        candidate_multiplier: int = 4,
        fast_mode: bool = True,
        retrieval_scope: str = "active_only",
        freshness_weight: float | None = None,
        dedup_by_family: bool | None = None,
    ) -> dict:
        rewritten = rewritten_query or (query if fast_mode else self.rewriter.rewrite(query))
        final_scope = retrieval_scope or settings.default_retrieval_scope
        final_freshness = settings.default_freshness_weight if freshness_weight is None else float(freshness_weight)
        final_dedup = settings.default_dedup_by_family if dedup_by_family is None else bool(dedup_by_family)
        chunk_map = self.repo.get_kb_chunk_map(kb_id=kb_id, retrieval_scope=final_scope)
        hits = []
        if chunk_map:
            hits = self._retrieve_hits(
                kb_id=kb_id,
                query=query,
                rewritten=rewritten,
                chunk_map=chunk_map,
                top_k=top_k,
                candidate_multiplier=candidate_multiplier,
                fast_mode=fast_mode,
                retrieval_scope=final_scope,
                freshness_weight=final_freshness,
                dedup_by_family=final_dedup,
            )

        return {
            "kb_id": kb_id,
            "query": query,
            "rewritten_query": rewritten,
            "params": {
                "top_k": top_k,
                "candidate_multiplier": candidate_multiplier,
                "fast_mode": fast_mode,
                "retrieval_scope": final_scope,
                "freshness_weight": final_freshness,
                "dedup_by_family": final_dedup,
            },
            "top_hits": [self._citation_from_hit(hit) for hit in hits],
        }

    def _retrieve_hits(
        self,
        kb_id: str,
        query: str,
        rewritten: str,
        chunk_map: dict[str, dict],
        top_k: int,
        candidate_multiplier: int,
        fast_mode: bool,
        retrieval_scope: str,
        freshness_weight: float,
        dedup_by_family: bool,
    ):
        # 检索流水线：
        # 关键词过滤（可选） -> 混合检索 -> 轻关键词加分 -> 重排 -> 新鲜度+去重
        active_chunk_map, keyword_meta = self._apply_keyword_layer(query=rewritten, chunk_map=chunk_map)
        effective_multiplier = 2 if fast_mode else candidate_multiplier
        hits = self.retriever.search(
            kb_id=kb_id,
            query=rewritten,
            kb_chunk_map=active_chunk_map,
            top_k=top_k,
            candidate_multiplier=effective_multiplier,
        )
        hits = self._apply_weak_keyword_boost(hits=hits, keywords=keyword_meta.get("weak", []))
        if not fast_mode:
            hits = self.reranker.rerank(rewritten, hits, top_k=top_k)
        else:
            hits = hits[:top_k]
        hits = self._apply_freshness_and_dedup(
            hits=hits,
            top_k=top_k,
            dedup_by_family=dedup_by_family,
            freshness_weight=freshness_weight,
            retrieval_scope=retrieval_scope,
        )
        return hits

    @staticmethod
    def _citation_from_hit(hit) -> dict:
        # 把内部检索命中对象转换成 API 返回格式，前端可直接渲染来源与预览内容。
        metadata = hit.metadata or {}
        source_type = metadata.get("source_type", "text")
        file_suffix = metadata.get("file_suffix", "")
        is_image = source_type == "image" or file_suffix in {".png", ".jpg", ".jpeg", ".bmp", ".webp", ".tif", ".tiff"}

        return {
            "chunk_id": hit.chunk_id,
            "doc_id": hit.doc_id,
            "score": hit.score,
            "bm25_score": hit.bm25_score,
            "vector_score": hit.vector_score,
            "rrf_score": hit.rrf_score,
            "rerank_score": hit.rerank_score,
            "source_file_path": metadata.get("file_path", ""),
            "source_file_name": metadata.get("file_name", ""),
            "source_type": source_type,
            "display_type": "image" if is_image else "text",
            "asset_url": f"/knowledge-bases/documents/{hit.doc_id}/asset",
            "preview_text": hit.text[:220],
        }

    def _apply_keyword_layer(self, query: str, chunk_map: dict[str, dict]) -> tuple[dict[str, dict], dict]:
        # 强关键词过滤层：用于缩小候选集合，提高召回精度和效率。
        # 保护机制：若过滤后太少，会自动回退到不过滤，避免“误杀”。
        if not settings.enable_keyword_layer:
            return chunk_map, {"strong": [], "weak": [], "enabled": False}

        strong = self._extract_strong_keywords(query)
        weak = self._extract_weak_keywords(query)
        if not strong:
            return chunk_map, {"strong": strong, "weak": weak, "enabled": False}

        kept: dict[str, dict] = {}
        lowered = [x.lower() for x in strong]
        for chunk_id, row in chunk_map.items():
            metadata = row.get("metadata", {}) or {}
            searchable = " ".join(
                [
                    row.get("text", ""),
                    json.dumps(metadata, ensure_ascii=False),
                ]
            ).lower()
            if any(token in searchable for token in lowered):
                kept[chunk_id] = row

        safe_floor = max(
            settings.keyword_layer_min_keep_count,
            int(len(chunk_map) * settings.keyword_layer_min_keep_ratio),
        )
        if len(kept) < safe_floor:
            return chunk_map, {"strong": strong, "weak": weak, "enabled": False}
        return kept, {"strong": strong, "weak": weak, "enabled": True}

    @staticmethod
    def _extract_strong_keywords(query: str) -> list[str]:
        strong: list[str] = []
        if settings.keyword_strong_pattern_enabled:
            for token in re.findall(r"[A-Z]{2,}[A-Z0-9_\-]{1,}|[A-Z]{1,}\d{2,}", query):
                if token not in strong:
                    strong.append(token)
        for token in re.findall(r"[\u4e00-\u9fff]{2,8}", query):
            if any(key in token for key in ["系统", "告警", "数据库", "工单", "连接池", "网关", "服务"]):
                if token not in strong:
                    strong.append(token)
        return strong[: settings.keyword_model_max_terms]

    @staticmethod
    def _extract_weak_keywords(query: str) -> list[str]:
        weak: list[str] = []
        for token in re.findall(r"[\u4e00-\u9fff]{2,8}|[a-zA-Z][a-zA-Z0-9_\-]{2,}", query):
            token = token.strip()
            if token and token not in weak:
                weak.append(token)
        return weak[: settings.keyword_model_max_terms]

    @staticmethod
    def _apply_weak_keyword_boost(hits: list, keywords: list[str]) -> list:
        # 弱关键词只是“轻微加分”，不会替代主检索分数。
        if not keywords:
            return hits
        lowered = [x.lower() for x in keywords]
        for hit in hits:
            joined = f"{hit.text} {json.dumps(hit.metadata or {}, ensure_ascii=False)}".lower()
            matched = sum(1 for token in lowered if token in joined)
            if matched > 0:
                hit.score += min(0.12, 0.02 * matched)
        hits.sort(key=lambda item: item.score, reverse=True)
        return hits

    @staticmethod
    def _apply_freshness_and_dedup(
        hits: list,
        top_k: int,
        dedup_by_family: bool,
        freshness_weight: float,
        retrieval_scope: str,
    ) -> list:
        # 对候选结果进行二次排序：
        # - active_only 模式可加入“新鲜度”偏好
        # - 可按文档家族去重，避免同一文档多个版本挤占 top_k
        if not hits:
            return []

        enriched = []
        times = []
        for hit in hits:
            metadata = hit.metadata or {}
            effective_at = metadata.get("effective_at", "")
            ts = 0.0
            if isinstance(effective_at, str) and effective_at:
                try:
                    ts = float(
                        time.mktime(
                            time.strptime(
                                effective_at.replace("T", " ").replace("Z", "").split("+")[0][:19],
                                "%Y-%m-%d %H:%M:%S",
                            )
                        )
                    )
                except Exception:
                    ts = 0.0
            times.append(ts)
            enriched.append((hit, metadata.get("doc_family_id", hit.doc_id), ts))

        low = min(times) if times else 0.0
        high = max(times) if times else 0.0
        span = max(1.0, high - low)

        rescored = []
        for hit, family, ts in enriched:
            freshness = (ts - low) / span
            # 历史模式下不强行加时间权重，避免干扰追溯。
            score = hit.score + (freshness_weight * freshness if retrieval_scope == "active_only" else 0.0)
            rescored.append((score, family, ts, hit))

        rescored.sort(key=lambda item: (item[0], item[2]), reverse=True)
        if not dedup_by_family:
            return [item[3] for item in rescored[:top_k]]

        picked = []
        seen = set()
        for _, family, _, hit in rescored:
            if family in seen:
                continue
            seen.add(family)
            picked.append(hit)
            if len(picked) >= top_k:
                break
        return picked

    def _build_messages(self, query: str, rewritten: str, hits: list, memory_context: str = "") -> list[dict[str, str]]:
        # 将检索结果和会话记忆拼成大模型输入提示词。
        if not hits:
            return [
                {"role": "system", "content": "You are an operations knowledge assistant. Keep answers actionable."},
                {
                    "role": "user",
                    "content": "No context is available from knowledge base. Explain that answer is not grounded and ask user to ingest data.",
                },
            ]

        context = "\n\n".join([f"[{idx + 1}] {hit.text}" for idx, hit in enumerate(hits)])
        memory_block = f"\nConversation memory:\n{memory_context}\n" if memory_context else ""
        system_prompt = (
            "You are the Hangzhou Bank operations center assistant. "
            "Answer only from retrieved context and conversation memory. "
            "If evidence is insufficient, say so and provide next troubleshooting steps."
        )
        user_prompt = (
            f"Original question: {query}\n"
            f"Rewritten query: {rewritten}\n"
            f"Retrieved context:\n{context}\n"
            f"{memory_block}\n"
            "Output format:\n"
            "1) Conclusion\n"
            "2) Step-by-step actions\n"
            "3) Risks and rollback plan"
        )
        return [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

    def _generate_answer(self, query: str, rewritten: str, hits: list, memory_context: str = "") -> str:
        messages = self._build_messages(query=query, rewritten=rewritten, hits=hits, memory_context=memory_context)
        try:
            return self.llm_client.chat(messages=messages, model=settings.siliconflow_chat_model)
        except SiliconFlowError:
            preview = "\n".join([f"[{idx + 1}] {hit.text[:220]}" for idx, hit in enumerate(hits)])
            return "Model call failed. Retrieved snippets:\n" + preview

    def _generate_answer_stream(self, query: str, rewritten: str, hits: list, memory_context: str = "") -> Iterator[str]:
        messages = self._build_messages(query=query, rewritten=rewritten, hits=hits, memory_context=memory_context)
        try:
            for token in self.llm_client.chat_stream(messages=messages, model=settings.siliconflow_chat_model):
                yield token
        except SiliconFlowError:
            yield "Streaming model call failed. Check SiliconFlow key/network/model settings."

    def _build_memory_context(self, kb_id: str, session_id: str, use_memory: bool) -> tuple[str, dict]:
        # 读取并压缩历史对话，避免上下文过长导致 token 浪费或超限。
        if not use_memory or not session_id:
            return "", {
                "enabled": False,
                "session_id": session_id,
                "max_turns": settings.conversation_max_turns,
                "max_chars": settings.conversation_max_chars,
                "summary_max_chars": settings.conversation_summary_max_chars,
                "used_turns": 0,
                "compressed": False,
            }

        rows = self.meta.get_conversation_messages(
            session_id=session_id,
            kb_id=kb_id,
            limit=max(2 * settings.conversation_max_turns + 20, 40),
        )
        if not rows:
            return "", {
                "enabled": True,
                "session_id": session_id,
                "max_turns": settings.conversation_max_turns,
                "max_chars": settings.conversation_max_chars,
                "summary_max_chars": settings.conversation_summary_max_chars,
                "used_turns": 0,
                "compressed": False,
            }

        max_msgs = max(2, 2 * settings.conversation_max_turns)
        selected = rows[-max_msgs:]
        content_lines = [f"{row['role']}: {row['content']}" for row in selected]
        raw_text = "\n".join(content_lines)

        compressed = False
        if len(raw_text) > settings.conversation_max_chars:
            raw_text = self._compress_memory(content_lines)
            compressed = True

        return raw_text, {
            "enabled": True,
            "session_id": session_id,
            "max_turns": settings.conversation_max_turns,
            "max_chars": settings.conversation_max_chars,
            "summary_max_chars": settings.conversation_summary_max_chars,
            "used_turns": len(selected) // 2,
            "compressed": compressed,
        }

    @staticmethod
    def _compress_memory(lines: list[str]) -> str:
        # 简单压缩策略：保留最近若干轮，并对超长行做“首尾截断”。
        parts = []
        for line in lines[-16:]:
            text = line.strip()
            if len(text) <= 120:
                parts.append(text)
            else:
                parts.append(text[:70] + " ... " + text[-40:])
        merged = "\n".join(parts)
        return merged[: settings.conversation_summary_max_chars]

    def _save_conversation_turn(self, session_id: str, kb_id: str, query: str, answer: str) -> None:
        # 写入一问一答，并裁剪旧数据，防止会话表无限膨胀。
        self.meta.add_conversation_message(session_id=session_id, kb_id=kb_id, role="user", content=query)
        self.meta.add_conversation_message(session_id=session_id, kb_id=kb_id, role="assistant", content=answer)
        self.meta.delete_conversation_messages_before(
            session_id=session_id,
            kb_id=kb_id,
            max_keep=max(2 * settings.conversation_max_turns + 20, 40),
        )

    @staticmethod
    def _make_cache_key(
        kb_id: str,
        query: str,
        rewritten: str,
        top_k: int,
        candidate_multiplier: int,
        fast_mode: bool,
        session_id: str,
        use_memory: bool,
        retrieval_scope: str,
        freshness_weight: float,
        dedup_by_family: bool,
    ) -> str:
        return "|".join(
            [
                kb_id,
                query,
                rewritten,
                str(top_k),
                str(candidate_multiplier),
                str(int(fast_mode)),
                session_id,
                str(int(use_memory)),
                retrieval_scope,
                f"{freshness_weight:.4f}",
                str(int(dedup_by_family)),
            ]
        )

    def record_bad_case(
        self,
        kb_id: str,
        query: str,
        rewritten_query: str,
        feedback: str,
        retrieval_snapshot: dict | None = None,
        auto_capture_snapshot: bool = True,
        top_k: int = 5,
        candidate_multiplier: int = 4,
        fast_mode: bool = True,
        category: str = "retrieval",
        severity: str = "medium",
        status: str = "open",
        expected_answer: str = "",
        retrieval_scope: str = "active_only",
        freshness_weight: float | None = None,
        dedup_by_family: bool | None = None,
    ) -> dict:
        final_rewritten = rewritten_query or (query if fast_mode else self.rewriter.rewrite(query))
        final_scope = retrieval_scope or settings.default_retrieval_scope
        final_freshness = settings.default_freshness_weight if freshness_weight is None else float(freshness_weight)
        final_dedup = settings.default_dedup_by_family if dedup_by_family is None else bool(dedup_by_family)

        final_snapshot = retrieval_snapshot or {}
        if auto_capture_snapshot and not final_snapshot:
            final_snapshot = self.build_retrieval_snapshot(
                kb_id=kb_id,
                query=query,
                rewritten_query=final_rewritten,
                top_k=top_k,
                candidate_multiplier=candidate_multiplier,
                fast_mode=fast_mode,
                retrieval_scope=final_scope,
                freshness_weight=final_freshness,
                dedup_by_family=final_dedup,
            )

        self.meta.add_bad_case(
            kb_id=kb_id,
            query=query,
            rewritten_query=final_rewritten,
            feedback=feedback,
            retrieval_snapshot=json.dumps(final_snapshot, ensure_ascii=False),
            category=category,
            severity=severity,
            status=status,
            expected_answer=expected_answer,
        )

        if self.cache is not None:
            self.cache.invalidate_prefix(f"{kb_id}|")

        return {
            "status": "ok",
            "rewritten_query": final_rewritten,
            "snapshot_top_hits": len(final_snapshot.get("top_hits", [])) if isinstance(final_snapshot, dict) else 0,
            "bad_case": {
                "category": category,
                "severity": severity,
                "status": status,
                "expected_answer": expected_answer,
            },
            "retrieval_policy": {
                "retrieval_scope": final_scope,
                "freshness_weight": final_freshness,
                "dedup_by_family": final_dedup,
            },
        }
