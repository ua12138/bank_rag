from __future__ import annotations

import math
import time
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor

from hz_bank_rag.core.types import RetrievalHit
from hz_bank_rag.storage.bm25_store import BM25Store
from hz_bank_rag.storage.vector_store import BaseVectorStore


class HybridRetriever:
    """混合检索器：把 BM25（关键词）与向量检索（语义）融合。"""

    def __init__(self, bm25_store: BM25Store, vector_store: BaseVectorStore) -> None:
        self.bm25_store = bm25_store
        self.vector_store = vector_store

    def search(
        self,
        kb_id: str,
        query: str,
        kb_chunk_map: dict[str, dict],
        top_k: int = 5,
        candidate_multiplier: int = 4,
    ) -> list[RetrievalHit]:
        hits, _ = self.search_with_trace(
            kb_id=kb_id,
            query=query,
            kb_chunk_map=kb_chunk_map,
            top_k=top_k,
            candidate_multiplier=candidate_multiplier,
        )
        return hits

    def search_with_trace(
        self,
        kb_id: str,
        query: str,
        kb_chunk_map: dict[str, dict],
        top_k: int = 5,
        candidate_multiplier: int = 4,
    ) -> tuple[list[RetrievalHit], dict[str, int]]:
        # candidate_k 通常 > top_k：
        # 先“宽召回”更多候选，再在后续阶段（重排/去重）收缩到 top_k。
        t0 = time.perf_counter()
        candidate_k = max(top_k * candidate_multiplier, top_k)

        use_milvus_sparse = bool(
            hasattr(self.vector_store, "search_sparse") and getattr(self.vector_store, "sparse_available", False)
        )

        # 稀疏检索 + 稠密检索并行执行，降低端到端延迟。
        with ThreadPoolExecutor(max_workers=2) as pool:
            if use_milvus_sparse:
                sparse_future = pool.submit(self.vector_store.search_sparse, query=query, kb_id=kb_id, top_k=candidate_k)
            else:
                sparse_future = pool.submit(self.bm25_store.search, kb_id=kb_id, query=query, top_k=candidate_k)
            dense_future = pool.submit(self.vector_store.search, query=query, kb_id=kb_id, top_k=candidate_k)
            sparse_hits = sparse_future.result()
            t_sparse = time.perf_counter()
            dense_hits = dense_future.result()
            t_dense = time.perf_counter()

        sparse_norm = self._normalize_scores(sparse_hits)
        dense_norm = self._normalize_scores(dense_hits)

        rank_map: dict[str, dict[str, float]] = defaultdict(dict)
        for rank, (chunk_id, score) in enumerate(sparse_hits, start=1):
            rank_map[chunk_id]["bm25_rank"] = rank
            rank_map[chunk_id]["bm25_score"] = score
            rank_map[chunk_id]["bm25_norm"] = sparse_norm.get(chunk_id, 0.0)
        for rank, (chunk_id, score) in enumerate(dense_hits, start=1):
            rank_map[chunk_id]["vector_rank"] = rank
            rank_map[chunk_id]["vector_score"] = score
            rank_map[chunk_id]["vector_norm"] = dense_norm.get(chunk_id, 0.0)

        merged: list[RetrievalHit] = []
        for chunk_id, score_info in rank_map.items():
            chunk_row = kb_chunk_map.get(chunk_id)
            if chunk_row is None:
                continue

            # RRF（Reciprocal Rank Fusion）：用排名融合，不直接依赖不同模型分数尺度。
            rrf_score = self._rrf(score_info.get("bm25_rank")) + self._rrf(score_info.get("vector_rank"))

            # 归一化分数只做“轻微 tie-break”，避免同排名时完全打平。
            final_score = rrf_score + 0.2 * score_info.get("bm25_norm", 0.0) + 0.2 * score_info.get("vector_norm", 0.0)

            merged.append(
                RetrievalHit(
                    chunk_id=chunk_id,
                    doc_id=chunk_row["doc_id"],
                    text=chunk_row["text"],
                    score=final_score,
                    source="hybrid",
                    bm25_score=score_info.get("bm25_score", 0.0),
                    vector_score=score_info.get("vector_score", 0.0),
                    rrf_score=rrf_score,
                    metadata=chunk_row.get("metadata", {}),
                )
            )

        merged.sort(key=lambda hit: hit.score, reverse=True)
        t1 = time.perf_counter()
        trace = {
            "bm25_vector_recall_ms": int((max(t_sparse, t_dense) - t0) * 1000),
            "rrf_fusion_ms": int((t1 - max(t_sparse, t_dense)) * 1000),
        }
        return merged[:candidate_k], trace

    @staticmethod
    def _rrf(rank: int | None, k: int = 60) -> float:
        # rank 越靠前（数字越小）分数越高；缺失 rank 返回 0。
        if rank is None:
            return 0.0
        return 1.0 / (k + rank)

    @staticmethod
    def _normalize_scores(hits: list[tuple[str, float]]) -> dict[str, float]:
        # Min-Max 归一化到 [0,1]，用于不同检索器分数的温和对齐。
        if not hits:
            return {}
        values = [score for _, score in hits]
        high = max(values)
        low = min(values)
        if math.isclose(high, low):
            return {chunk_id: 1.0 for chunk_id, _ in hits}
        return {chunk_id: (score - low) / (high - low) for chunk_id, score in hits}
