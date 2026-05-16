from __future__ import annotations

import json
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from fastapi.responses import HTMLResponse
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
from hz_bank_rag.core.siliconflow_client import SiliconFlowClient
from hz_bank_rag.evaluation.ragas_runner import RagasRunner
from hz_bank_rag.retrieval.hybrid_retriever import HybridRetriever
from hz_bank_rag.retrieval.query_rewrite import QueryRewriter
from hz_bank_rag.retrieval.reranker import SiliconFlowReranker
from hz_bank_rag.service.qa_service import QAService
from hz_bank_rag.service.kg_service import KnowledgeGraphService
from hz_bank_rag.storage.bm25_store import BM25Store
from hz_bank_rag.storage.metadata_store import MetadataStore
from hz_bank_rag.storage.rag_repository import DuplicateDocumentError, RAGRepository
from hz_bank_rag.storage.vector_store import InMemoryVectorStore, MilvusVectorStore


def build_app() -> FastAPI:
    # 应用装配入口：这里把"存储层 + 检索层 + 服务层 + HTTP 路由"一次性连接起来。
    app = FastAPI(
        title="HZ Bank Production RAG",
        version="0.5.0",
        description="Hangzhou Bank production operation center intelligent QA system.",
    )

    # 1) 元数据存储（SQLite）：文档信息、分块信息、会话记忆、bad case 都在这里。
    meta = MetadataStore(settings.sqlite_path)
    # 2) 稀疏检索器（BM25）：负责关键词匹配。
    bm25 = BM25Store()
    # 3) 向量检索器：可切换 Milvus（生产）或内存版（本地学习/测试）。
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

    # 5) 检索层：把 BM25 + 向量检索融合。
    retriever = HybridRetriever(bm25_store=bm25, vector_store=vector_store)
    # 6) 问答服务层：把改写、检索、重排、生成答案组织成一条流水线。
    qa_service = QAService(
        repo=None,  # 占位，下面创建 repo 后再赋值
        retriever=retriever,
        rewriter=QueryRewriter(),
        reranker=SiliconFlowReranker(),
        meta=meta,
    )
    ragas_runner = RagasRunner()
    kg_service = KnowledgeGraphService()

    # 缓存失效回调：文档入库/删除时，按 kb_id 失效 L2 检索缓存和 L3 答案缓存。
    def _invalidate_caches(changed_kb_id: str) -> None:
        if qa_service.retrieval_cache is not None:
            qa_service.retrieval_cache.invalidate_kb(changed_kb_id)
        if qa_service.cache is not None:
            qa_service.cache.invalidate_kb(changed_kb_id)

    # 4) 仓储层：统一封装"文档入库、切分、索引重建、删除"等能力。
    repo = RAGRepository(metadata=meta, vector_store=vector_store, bm25=bm25, on_kb_change=_invalidate_caches)
    qa_service.repo = repo

    @app.get("/health")
    def health() -> dict:
        # 健康检查：逐组件探测运行状态，并返回关键配置。
        component_health = {
            "metadata_store": meta.health(),
            "bm25_store": bm25.health(),
            "vector_store": vector_store.health(),
            "llm_client": SiliconFlowClient().health(),
        }
        all_ok = all(c.get("status") == "ok" for c in component_health.values())
        return {
            "status": "ok" if all_ok else "degraded",
            "components": component_health,
            "app": settings.app_name,
            "use_milvus": settings.use_milvus,
            "milvus_uri": settings.milvus_uri,
            "siliconflow_base_url": settings.siliconflow_base_url,
            "siliconflow_chat_model": settings.siliconflow_chat_model,
            "siliconflow_embedding_model": settings.siliconflow_embedding_model,
            "siliconflow_rerank_model": settings.siliconflow_rerank_model,
            "siliconflow_vision_model": settings.siliconflow_vision_model,
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
        # 单文档入库入口：文件 -> 解析 -> 清洗 -> 分块 -> 向量/BM25 索引。
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
        # 同步问答：一次请求直接返回完整答案。
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
                enable_kg=req.enable_kg,
                kg_hop_limit=req.kg_hop_limit,
            )
        except RuntimeError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.post("/query/stream")
    def query_stream(req: QueryRequest) -> StreamingResponse:
        # 流式问答：先返回元信息，再按 token 逐步返回答案（SSE 协议）。
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
            # 前端需要先拿到 citations 等元数据，再消费 token 流。
            yield f"data: {json.dumps({'type': 'meta', 'payload': meta_info}, ensure_ascii=False)}\n\n"
            for token in token_iter:
                yield f"data: {json.dumps({'type': 'token', 'payload': token}, ensure_ascii=False)}\n\n"
            yield "data: {\"type\":\"done\"}\n\n"

        return StreamingResponse(event_generator(), media_type="text/event-stream")

    @app.post("/bad-cases")
    def bad_case(req: BadCaseRequest) -> dict:
        # bad case 记录入口：用于沉淀线上失败样本，支持后续评估与回归。
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
        # 拉取多轮会话历史，用于调试 memory 是否生效。
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
        # 轻量评估：用于快速验证改动前后效果趋势。
        return ragas_runner.evaluate(req.dataset, pipeline="lightweight")

    @app.post("/evaluate/ragas/official")
    def evaluate_ragas_official(req: EvalRequest) -> dict:
        # 官方评估：指标更全，耗时通常更高。
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

    @app.post("/kg/rebuild")
    def kg_rebuild(
        kb_id: str = Query(..., description="Knowledge base id"),
        retrieval_scope: str = Query(default="active_only", description="active_only|include_history"),
    ) -> dict:
        chunks = repo.get_kb_chunk_map(kb_id=kb_id, retrieval_scope=retrieval_scope)
        return kg_service.rebuild(kb_id=kb_id, chunks=list(chunks.values()))

    @app.get("/kg/entities/search")
    def kg_entities_search(
        kb_id: str = Query(...),
        keyword: str = Query(...),
        limit: int = Query(default=20, ge=1, le=200),
    ) -> dict:
        return {"kb_id": kb_id, "entities": kg_service.entities_search(kb_id=kb_id, keyword=keyword, limit=limit)}

    @app.get("/kg/subgraph")
    def kg_subgraph(
        kb_id: str = Query(...),
        entity: str = Query(...),
        hop: int = Query(default=2, ge=1, le=4),
    ) -> dict:
        data = kg_service.subgraph(kb_id=kb_id, entity=entity, hop=hop)
        return {"kb_id": kb_id, "entity": entity, "hop": hop, **data}

    @app.get("/kg/path")
    def kg_path(
        kb_id: str = Query(...),
        source: str = Query(...),
        target: str = Query(...),
    ) -> dict:
        data = kg_service.shortest_path(kb_id=kb_id, source=source, target=target)
        return {"kb_id": kb_id, "source": source, "target": target, **data}

    @app.get("/metrics/overview")
    def metrics_overview(kb_id: str | None = Query(default=None)) -> dict:
        return meta.metrics_overview(kb_id=kb_id)

    @app.get("/metrics/tokens")
    def metrics_tokens(kb_id: str | None = Query(default=None)) -> dict:
        return meta.token_overview(kb_id=kb_id)

    @app.get("/metrics/latency/stages")
    def metrics_latency_stages(kb_id: str | None = Query(default=None)) -> dict:
        return meta.metrics_overview(kb_id=kb_id)

    @app.get("/metrics/requests")
    def metrics_requests(
        kb_id: str | None = Query(default=None),
        session_id: str | None = Query(default=None),
        limit: int = Query(default=100, ge=1, le=1000),
    ) -> dict:
        rows = meta.list_query_metrics(kb_id=kb_id, session_id=session_id, limit=limit)
        return {"count": len(rows), "rows": rows}

    @app.get("/ui/kg", response_class=HTMLResponse)
    def ui_kg() -> str:
        return """
<!doctype html><html><head><meta charset='utf-8'><title>KG Console</title></head>
<body><h1>KG Console</h1><p>Use APIs: /kg/rebuild, /kg/entities/search, /kg/subgraph, /kg/path</p></body></html>
"""

    @app.get("/ui/metrics", response_class=HTMLResponse)
    def ui_metrics() -> str:
        return """
<!doctype html><html><head><meta charset='utf-8'><title>Metrics Console</title></head>
<body><h1>Metrics Console</h1><p>Use APIs: /metrics/overview, /metrics/tokens, /metrics/latency/stages, /metrics/requests</p></body></html>
"""

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
