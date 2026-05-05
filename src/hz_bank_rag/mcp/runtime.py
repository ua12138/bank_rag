from __future__ import annotations

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
    meta: MetadataStore
    repo: RAGRepository
    qa: QAService
    ragas: RagasRunner
    vector_store: InMemoryVectorStore | MilvusVectorStore


def build_runtime() -> Runtime:
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

    repo = RAGRepository(metadata=meta, vector_store=vector_store, bm25=bm25)
    retriever = HybridRetriever(bm25_store=bm25, vector_store=vector_store)
    qa = QAService(
        repo=repo,
        retriever=retriever,
        rewriter=QueryRewriter(),
        reranker=SiliconFlowReranker(),
        meta=meta,
    )
    ragas = RagasRunner()

    return Runtime(meta=meta, repo=repo, qa=qa, ragas=ragas, vector_store=vector_store)
