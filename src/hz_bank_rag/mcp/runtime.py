from __future__ import annotations

"""MCP 运行时装配：构建 mcp.main 需要的依赖对象。"""

from dataclasses import dataclass

from hz_bank_rag.core.config import settings
from hz_bank_rag.evaluation.ragas_runner import RagasRunner
from hz_bank_rag.retrieval.hybrid_retriever import HybridRetriever
from hz_bank_rag.retrieval.query_rewrite import QueryRewriter
from hz_bank_rag.retrieval.reranker import SiliconFlowReranker
from hz_bank_rag.service.qa_service import QAService
from hz_bank_rag.storage.bm25_store import BM25Store
from hz_bank_rag.storage.metadata_store import MetadataStore
from hz_bank_rag.storage.rag_repository import RAGRepository
from hz_bank_rag.storage.vector_store import InMemoryVectorStore, MilvusVectorStore


@dataclass
class Runtime:
    """MCP 服务运行时对象集合。"""

    meta: MetadataStore
    repo: RAGRepository
    qa: QAService
    ragas: RagasRunner
    vector_store: InMemoryVectorStore | MilvusVectorStore


def build_runtime() -> Runtime:
    """按统一方式组装运行时依赖。"""
    meta = MetadataStore(settings.sqlite_path)
    bm25 = BM25Store()
    vector_store = (
        MilvusVectorStore(
            uri=settings.milvus_uri,
            dim=settings.vector_dim,
            token=settings.milvus_token,
            collection_name=settings.milvus_collection,
            consistency_level=settings.milvus_consistency_level,
            enable_dynamic_field=settings.milvus_enable_dynamic_field,
        )
        if settings.use_milvus
        else InMemoryVectorStore(settings.vector_dim)
    )
    retriever = HybridRetriever(bm25_store=bm25, vector_store=vector_store)
    qa = QAService(
        repo=None,
        retriever=retriever,
        rewriter=QueryRewriter(),
        reranker=SiliconFlowReranker(),
        meta=meta,
    )
    ragas = RagasRunner()

    def _invalidate_caches(changed_kb_id: str) -> None:
        if qa.retrieval_cache is not None:
            qa.retrieval_cache.invalidate_kb(changed_kb_id)
        if qa.cache is not None:
            qa.cache.invalidate_kb(changed_kb_id)

    repo = RAGRepository(metadata=meta, vector_store=vector_store, bm25=bm25, on_kb_change=_invalidate_caches)
    qa.repo = repo
    return Runtime(meta=meta, repo=repo, qa=qa, ragas=ragas, vector_store=vector_store)
