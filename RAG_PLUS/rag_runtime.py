from __future__ import annotations

"""RAG_PLUS 运行时：复用基础 QAService 并支持按路由选模型。"""

import copy
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

try:
    from hz_bank_rag.core.config import settings as base_settings
    from hz_bank_rag.core.siliconflow_client import SiliconFlowClient, SiliconFlowError
    from hz_bank_rag.retrieval.hybrid_retriever import HybridRetriever
    from hz_bank_rag.retrieval.query_rewrite import QueryRewriter
    from hz_bank_rag.retrieval.reranker import SiliconFlowReranker
    from hz_bank_rag.service.qa_service import QAService
    from hz_bank_rag.storage.bm25_store import BM25Store
    from hz_bank_rag.storage.metadata_store import MetadataStore
    from hz_bank_rag.storage.rag_repository import RAGRepository
    from hz_bank_rag.storage.vector_store import InMemoryVectorStore, MilvusVectorStore
except ModuleNotFoundError:
    project_root = Path(__file__).resolve().parents[1]
    src_dir = str(project_root / "src")
    if src_dir not in sys.path:
        sys.path.insert(0, src_dir)
    from hz_bank_rag.core.config import settings as base_settings
    from hz_bank_rag.core.siliconflow_client import SiliconFlowClient, SiliconFlowError
    from hz_bank_rag.retrieval.hybrid_retriever import HybridRetriever
    from hz_bank_rag.retrieval.query_rewrite import QueryRewriter
    from hz_bank_rag.retrieval.reranker import SiliconFlowReranker
    from hz_bank_rag.service.qa_service import QAService
    from hz_bank_rag.storage.bm25_store import BM25Store
    from hz_bank_rag.storage.metadata_store import MetadataStore
    from hz_bank_rag.storage.rag_repository import RAGRepository
    from hz_bank_rag.storage.vector_store import InMemoryVectorStore, MilvusVectorStore

from RAG_PLUS.router import RouteDecision


@dataclass
class RagRuntime:
    """RAG_PLUS 运行时对象集合。"""

    meta: MetadataStore
    repo: RAGRepository
    qa: QAService
    llm: SiliconFlowClient


def build_runtime() -> RagRuntime:
    """构建 RAG_PLUS 运行时依赖。"""
    meta = MetadataStore(base_settings.sqlite_path)
    bm25 = BM25Store()
    vector_store = (
        MilvusVectorStore(
            uri=base_settings.milvus_uri,
            dim=base_settings.vector_dim,
            token=base_settings.milvus_token,
            collection_name=base_settings.milvus_collection,
            consistency_level=base_settings.milvus_consistency_level,
            enable_dynamic_field=base_settings.milvus_enable_dynamic_field,
        )
        if base_settings.use_milvus
        else InMemoryVectorStore(base_settings.vector_dim)
    )

    repo = RAGRepository(metadata=meta, vector_store=vector_store, bm25=bm25)
    retriever = HybridRetriever(bm25_store=bm25, vector_store=vector_store)
    qa = QAService(
        repo=repo,
        retriever=retriever,
        rewriter=QueryRewriter(),
        reranker=SiliconFlowReranker(),
        meta=meta,
    )
    return RagRuntime(meta=meta, repo=repo, qa=qa, llm=SiliconFlowClient())


class AdaptiveQAExecutor:
    """自适应问答执行器。

    复用 QAService 的检索与记忆能力，并按路由结果选择模型。
    """

    def __init__(self, runtime: RagRuntime) -> None:
        self.runtime = runtime

    def ask(
        self,
        kb_id: str,
        query: str,
        route: RouteDecision,
        top_k: int,
        candidate_multiplier: int,
        session_id: str,
        use_memory: bool,
    ) -> dict[str, Any]:
        """执行一次按路由策略的问答。"""
        qa = self.runtime.qa
        start = time.perf_counter()

        # 简单问题跳过 rewrite，复杂问题启用 rewrite。
        fast_mode = route.level == "simple"
        rewritten = query if fast_mode else qa.rewriter.rewrite(query)

        chunk_map = qa.repo.get_kb_chunk_map(kb_id)
        if not chunk_map:
            return {
                "kb_id": kb_id,
                "query": query,
                "rewritten_query": rewritten,
                "answer": "Knowledge base is empty. Please ingest documents first.",
                "citations": [],
                "latency_ms": int((time.perf_counter() - start) * 1000),
            }

        effective_multiplier = 2 if fast_mode else candidate_multiplier
        hits = qa.retriever.search(
            kb_id=kb_id,
            query=rewritten,
            kb_chunk_map=chunk_map,
            top_k=top_k,
            candidate_multiplier=effective_multiplier,
        )
        if route.use_rerank and not fast_mode:
            hits = qa.reranker.rerank(rewritten, hits, top_k=top_k)
        else:
            hits = hits[:top_k]

        memory_context, memory_meta = qa._build_memory_context(kb_id=kb_id, session_id=session_id, use_memory=use_memory)
        messages = qa._build_messages(query=query, rewritten=rewritten, hits=hits, memory_context=memory_context)

        try:
            answer = self.runtime.llm.chat(messages=messages, model=route.selected_model)
        except SiliconFlowError:
            answer = "\n".join([f"[{idx + 1}] {hit.text[:220]}" for idx, hit in enumerate(hits)])
            answer = "Model call failed. Retrieved snippets:\n" + answer

        if session_id and use_memory:
            qa._save_conversation_turn(session_id=session_id, kb_id=kb_id, query=query, answer=answer)

        return {
            "kb_id": kb_id,
            "query": query,
            "rewritten_query": rewritten,
            "answer": answer,
            "session_id": session_id,
            "memory": memory_meta,
            "citations": [copy.deepcopy(qa._citation_from_hit(hit)) for hit in hits],
            "latency_ms": int((time.perf_counter() - start) * 1000),
        }
