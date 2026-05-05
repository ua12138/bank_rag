from __future__ import annotations

import json
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from fastapi.responses import StreamingResponse

from hz_bank_rag.api.schemas import (
    BadCaseRequest,
    BadCaseSnapshotRequest,
    BulkIngestRequest,
    EvalRequest,
    IngestRequest,
    QueryRequest,
    RagasBuildRequest,
)
from hz_bank_rag.core.config import settings
from hz_bank_rag.evaluation.ragas_runner import RagasRunner
from hz_bank_rag.retrieval.hybrid_retriever import HybridRetriever
from hz_bank_rag.retrieval.query_rewrite import QueryRewriter
from hz_bank_rag.retrieval.reranker import SiliconFlowReranker
from hz_bank_rag.service.qa_service import QAService
from hz_bank_rag.storage.bm25_store import BM25Store
from hz_bank_rag.storage.metadata_store import MetadataStore
from hz_bank_rag.storage.rag_repository import DuplicateDocumentError, RAGRepository
from hz_bank_rag.storage.vector_store import InMemoryVectorStore, MilvusVectorStore


def build_app() -> FastAPI:
    app = FastAPI(
        title="HZ Bank Production RAG",
        version="0.5.0",
        description="Hangzhou Bank production operation center intelligent QA system.",
    )

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
    qa_service = QAService(
        repo=repo,
        retriever=retriever,
        rewriter=QueryRewriter(),
        reranker=SiliconFlowReranker(),
        meta=meta,
    )
    ragas_runner = RagasRunner()

    @app.get("/health")
    def health() -> dict:
        return {
            "status": "ok",
            "app": settings.app_name,
            "use_milvus": settings.use_milvus,
            "milvus_uri": settings.milvus_uri,
            "vector_store": vector_store.__class__.__name__,
            "milvus_available": getattr(vector_store, "available", False),
            "siliconflow_base_url": settings.siliconflow_base_url,
            "siliconflow_chat_model": settings.siliconflow_chat_model,
            "siliconflow_embedding_model": settings.siliconflow_embedding_model,
            "siliconflow_rerank_model": settings.siliconflow_rerank_model,
            "siliconflow_vision_model": settings.siliconflow_vision_model,
            "siliconflow_key_configured": bool(settings.siliconflow_api_key),
            "query_cache": {
                "enabled": settings.enable_query_cache,
                "ttl_seconds": settings.query_cache_ttl_seconds,
                "max_size": settings.query_cache_max_size,
            },
            "conversation_memory": {
                "max_turns": settings.conversation_max_turns,
                "max_chars": settings.conversation_max_chars,
                "summary_max_chars": settings.conversation_summary_max_chars,
            },
        }

    @app.post("/knowledge-bases/{kb_id}/documents")
    def ingest_document(kb_id: str, req: IngestRequest) -> dict:
        try:
            return repo.ingest_document(
                kb_id=kb_id,
                file_path=req.file_path,
                parser_type=req.parser_type,
                chunk_strategy=req.chunk_strategy,
            )
        except FileNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except DuplicateDocumentError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        except RuntimeError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.post("/knowledge-bases/{kb_id}/documents/bulk")
    def bulk_ingest_documents(kb_id: str, req: BulkIngestRequest) -> dict:
        try:
            return repo.bulk_ingest(kb_id=kb_id, file_paths=req.file_paths, chunk_strategy=req.chunk_strategy)
        except RuntimeError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.get("/knowledge-bases/documents")
    def list_documents(
        kb_id: str | None = Query(default=None, description="Optional kb_id filter"),
        limit: int = Query(default=20, ge=1, le=200, description="Result limit"),
    ) -> list[dict]:
        return repo.list_documents(kb_id=kb_id, limit=limit)

    @app.delete("/knowledge-bases/{kb_id}/documents/{doc_id}")
    def delete_document(kb_id: str, doc_id: str) -> dict:
        return repo.delete_document(kb_id=kb_id, doc_id=doc_id)

    @app.delete("/knowledge-bases/{kb_id}")
    def delete_kb(kb_id: str) -> dict:
        return repo.delete_kb(kb_id)

    @app.post("/query")
    def query(req: QueryRequest) -> dict:
        try:
            return qa_service.ask(
                kb_id=req.kb_id,
                query=req.query,
                top_k=req.top_k,
                candidate_multiplier=req.candidate_multiplier,
                fast_mode=req.fast_mode,
                session_id=req.session_id,
                use_memory=req.use_memory,
                refresh_cache=req.refresh_cache,
                retrieval_scope=req.retrieval_scope,
                freshness_weight=req.freshness_weight,
                dedup_by_family=req.dedup_by_family,
            )
        except RuntimeError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.post("/query/stream")
    def query_stream(req: QueryRequest) -> StreamingResponse:
        try:
            meta_info, token_iter = qa_service.ask_stream(
                kb_id=req.kb_id,
                query=req.query,
                top_k=req.top_k,
                candidate_multiplier=req.candidate_multiplier,
                fast_mode=req.fast_mode,
                session_id=req.session_id,
                use_memory=req.use_memory,
                retrieval_scope=req.retrieval_scope,
                freshness_weight=req.freshness_weight,
                dedup_by_family=req.dedup_by_family,
            )
        except RuntimeError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

        def event_generator():
            yield f"data: {json.dumps({'type': 'meta', 'payload': meta_info}, ensure_ascii=False)}\n\n"
            for token in token_iter:
                yield f"data: {json.dumps({'type': 'token', 'payload': token}, ensure_ascii=False)}\n\n"
            yield "data: {\"type\":\"done\"}\n\n"

        return StreamingResponse(event_generator(), media_type="text/event-stream")

    @app.post("/bad-cases")
    def bad_case(req: BadCaseRequest) -> dict:
        return qa_service.record_bad_case(
            kb_id=req.kb_id,
            query=req.query,
            rewritten_query=req.rewritten_query,
            feedback=req.feedback,
            retrieval_snapshot=req.retrieval_snapshot,
            auto_capture_snapshot=req.auto_capture_snapshot,
            top_k=req.top_k,
            candidate_multiplier=req.candidate_multiplier,
            fast_mode=req.fast_mode,
            category=req.category,
            severity=req.severity,
            status=req.status,
            expected_answer=req.expected_answer,
            retrieval_scope=req.retrieval_scope,
            freshness_weight=req.freshness_weight,
            dedup_by_family=req.dedup_by_family,
        )

    @app.post("/bad-cases/snapshot")
    def build_bad_case_snapshot(req: BadCaseSnapshotRequest) -> dict:
        return qa_service.build_retrieval_snapshot(
            kb_id=req.kb_id,
            query=req.query,
            rewritten_query=req.rewritten_query,
            top_k=req.top_k,
            candidate_multiplier=req.candidate_multiplier,
            fast_mode=req.fast_mode,
            retrieval_scope=req.retrieval_scope,
            freshness_weight=req.freshness_weight,
            dedup_by_family=req.dedup_by_family,
        )

    @app.get("/bad-cases")
    def list_bad_cases(
        kb_id: str | None = Query(default=None, description="Optional kb_id filter"),
        limit: int = Query(default=50, ge=1, le=500, description="Result limit"),
    ) -> list[dict]:
        return meta.list_bad_cases(kb_id=kb_id, limit=limit)

    @app.get("/bad-cases/ragas-dataset")
    def bad_cases_to_ragas_dataset(
        kb_id: str = Query(..., description="Knowledge base id"),
        limit: int = Query(default=50, ge=1, le=200, description="Result limit"),
        fill_answer: bool = Query(default=True, description="Run current pipeline to fill answer"),
    ) -> dict:
        rows = meta.list_bad_case_for_ragas(kb_id=kb_id, limit=limit)
        dataset = []
        for row in rows:
            answer = ""
            if fill_answer:
                result = qa_service.ask(
                    kb_id=kb_id,
                    query=row["question"],
                    top_k=settings.search_top_k,
                    candidate_multiplier=settings.candidate_multiplier,
                    fast_mode=True,
                    refresh_cache=True,
                )
                answer = result.get("answer", "")
            dataset.append(
                {
                    "question": row["question"],
                    "answer": answer,
                    "contexts": row["contexts"],
                    "ground_truth": row["ground_truth"],
                    "bad_case_id": row["bad_case_id"],
                }
            )
        return {"kb_id": kb_id, "rows": len(dataset), "dataset": dataset}

    @app.get("/conversations/{session_id}")
    def get_conversation(
        session_id: str,
        kb_id: str = Query(..., description="Knowledge base id"),
        limit: int = Query(default=40, ge=1, le=200, description="Result limit"),
    ) -> dict:
        messages = meta.get_conversation_messages(session_id=session_id, kb_id=kb_id, limit=limit)
        return {
            "session_id": session_id,
            "kb_id": kb_id,
            "messages": messages,
            "memory_limits": {
                "conversation_max_turns": settings.conversation_max_turns,
                "conversation_max_chars": settings.conversation_max_chars,
                "conversation_summary_max_chars": settings.conversation_summary_max_chars,
            },
        }

    @app.post("/evaluate/ragas")
    def evaluate_ragas(req: EvalRequest) -> dict:
        return ragas_runner.evaluate(req.dataset, pipeline="lightweight")

    @app.post("/evaluate/ragas/official")
    def evaluate_ragas_official(req: EvalRequest) -> dict:
        return ragas_runner.evaluate(req.dataset, pipeline="official")

    @app.post("/evaluate/ragas/ab")
    def evaluate_ragas_ab(req: EvalRequest) -> dict:
        return ragas_runner.evaluate_ab(req.dataset)

    @app.post("/evaluate/ragas/dataset/build")
    def build_ragas_dataset(req: RagasBuildRequest) -> dict:
        dataset = []
        for sample in req.samples:
            result = qa_service.ask(
                kb_id=req.kb_id,
                query=sample.question,
                top_k=req.top_k,
                candidate_multiplier=req.candidate_multiplier,
                fast_mode=req.fast_mode,
                use_memory=False,
                refresh_cache=True,
            )
            contexts = [item.get("preview_text", "") for item in result.get("citations", [])]
            dataset.append(
                {
                    "question": sample.question,
                    "answer": result.get("answer", ""),
                    "contexts": contexts,
                    "ground_truth": sample.ground_truth,
                }
            )
        return {"kb_id": req.kb_id, "rows": len(dataset), "dataset": dataset}

    @app.get("/knowledge-bases/documents/{doc_id}/asset")
    def get_document_asset(doc_id: str) -> FileResponse:
        row = repo.get_document(doc_id)
        if row is None:
            raise HTTPException(status_code=404, detail=f"document not found: {doc_id}")
        file_path = Path(row["file_path"]).resolve()
        if not file_path.exists():
            raise HTTPException(status_code=404, detail=f"file not found: {file_path}")
        return FileResponse(path=str(file_path), filename=file_path.name)

    @app.post("/demo/seed")
    def seed_demo_data() -> dict:
        from hz_bank_rag.examples.seed_demo import seed_demo_data

        try:
            return seed_demo_data(repo=repo, kb_id=settings.default_kb_id, data_dir=Path(settings.data_dir))
        except RuntimeError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.get("/collections/policy")
    def get_collection_policy() -> dict:
        if hasattr(vector_store, "get_collection_policy"):
            return vector_store.get_collection_policy()
        return {"provider": vector_store.__class__.__name__, "managed": False}

    @app.get("/collections/managed")
    def list_managed_collections() -> dict:
        if hasattr(vector_store, "list_managed_collections"):
            return {
                "provider": vector_store.__class__.__name__,
                "collections": vector_store.list_managed_collections(),
            }
        return {"provider": vector_store.__class__.__name__, "collections": []}

    @app.post("/collections/cleanup")
    def cleanup_collections(dry_run: bool = Query(default=True, description="Only report, do not drop collections")) -> dict:
        if hasattr(vector_store, "cleanup_collections"):
            return vector_store.cleanup_collections(dry_run=dry_run)
        return {
            "provider": vector_store.__class__.__name__,
            "dry_run": dry_run,
            "cleaned": [],
            "note": "Collection cleanup is not supported for this vector store.",
        }

    return app


app = build_app()
