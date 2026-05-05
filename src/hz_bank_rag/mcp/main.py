from __future__ import annotations

"""MCP 包装服务：把 RAG 能力以 MCP/JSON-RPC 形式暴露。"""

from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from hz_bank_rag.core.config import settings
from hz_bank_rag.mcp.runtime import Runtime, build_runtime


class JsonRpcRequest(BaseModel):
    """JSON-RPC 请求模型。"""

    jsonrpc: str = "2.0"
    id: str | int | None = None
    method: str
    params: dict[str, Any] = Field(default_factory=dict)


class ToolCallRequest(BaseModel):
    """HTTP 版工具调用请求模型。"""

    name: str
    arguments: dict[str, Any] = Field(default_factory=dict)


def _tool_specs() -> list[dict[str, Any]]:
    """返回 MCP 可用工具元信息。"""
    return [
        {"name": "rag.health", "description": "Get runtime health and key configuration.", "inputSchema": {"type": "object", "properties": {}}},
        {
            "name": "rag.seed_demo",
            "description": "Ingest demo documents from data directory.",
            "inputSchema": {"type": "object", "properties": {"kb_id": {"type": "string"}, "data_dir": {"type": "string"}}},
        },
        {
            "name": "rag.query",
            "description": "Ask a question to RAG service.",
            "inputSchema": {
                "type": "object",
                "required": ["kb_id", "query"],
                "properties": {
                    "kb_id": {"type": "string"},
                    "query": {"type": "string"},
                    "top_k": {"type": "integer", "default": 5},
                    "candidate_multiplier": {"type": "integer", "default": 4},
                    "fast_mode": {"type": "boolean", "default": True},
                    "session_id": {"type": "string", "default": ""},
                    "use_memory": {"type": "boolean", "default": True},
                    "refresh_cache": {"type": "boolean", "default": False},
                },
            },
        },
        {
            "name": "rag.list_documents",
            "description": "List documents in knowledge base.",
            "inputSchema": {"type": "object", "properties": {"kb_id": {"type": "string"}, "limit": {"type": "integer", "default": 20}}},
        },
        {
            "name": "rag.submit_bad_case",
            "description": "Submit a bad-case record.",
            "inputSchema": {
                "type": "object",
                "required": ["kb_id", "query", "feedback"],
                "properties": {
                    "kb_id": {"type": "string"},
                    "query": {"type": "string"},
                    "feedback": {"type": "string"},
                    "rewritten_query": {"type": "string", "default": ""},
                    "category": {"type": "string", "default": "retrieval"},
                    "severity": {"type": "string", "default": "medium"},
                    "status": {"type": "string", "default": "open"},
                    "expected_answer": {"type": "string", "default": ""},
                },
            },
        },
        {
            "name": "rag.evaluate_ragas_ab",
            "description": "Run lightweight vs official ragas A/B comparison.",
            "inputSchema": {
                "type": "object",
                "required": ["dataset"],
                "properties": {
                    "dataset": {
                        "type": "array",
                        "items": {"type": "object", "required": ["question", "answer", "contexts", "ground_truth"]},
                    }
                },
            },
        },
        {
            "name": "rag.collection_policy",
            "description": "Get vector collection naming policy and lifecycle status.",
            "inputSchema": {"type": "object", "properties": {}},
        },
    ]


def _ok(req_id: str | int | None, result: dict[str, Any]) -> dict[str, Any]:
    """JSON-RPC 成功返回包。"""
    return {"jsonrpc": "2.0", "id": req_id, "result": result}


def _err(req_id: str | int | None, code: int, message: str) -> dict[str, Any]:
    """JSON-RPC 错误返回包。"""
    return {"jsonrpc": "2.0", "id": req_id, "error": {"code": code, "message": message}}


def _call_tool(runtime: Runtime, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    """工具分发函数：按工具名路由到具体实现。"""
    if name == "rag.health":
        return {
            "status": "ok",
            "app": settings.app_name,
            "use_milvus": settings.use_milvus,
            "milvus_uri": settings.milvus_uri,
            "siliconflow_chat_model": settings.siliconflow_chat_model,
            "siliconflow_embedding_model": settings.siliconflow_embedding_model,
            "siliconflow_key_configured": bool(settings.siliconflow_api_key),
        }
    if name == "rag.seed_demo":
        from hz_bank_rag.examples.seed_demo import seed_demo_data
        kb_id = str(arguments.get("kb_id") or settings.default_kb_id)
        data_dir = Path(str(arguments.get("data_dir") or settings.data_dir))
        return seed_demo_data(repo=runtime.repo, kb_id=kb_id, data_dir=data_dir)
    if name == "rag.query":
        kb_id = str(arguments.get("kb_id", ""))
        query = str(arguments.get("query", ""))
        if not kb_id or not query:
            raise ValueError("rag.query requires kb_id and query")
        return runtime.qa.ask(
            kb_id=kb_id,
            query=query,
            top_k=int(arguments.get("top_k", 5)),
            candidate_multiplier=int(arguments.get("candidate_multiplier", 4)),
            fast_mode=bool(arguments.get("fast_mode", True)),
            session_id=str(arguments.get("session_id", "")),
            use_memory=bool(arguments.get("use_memory", True)),
            refresh_cache=bool(arguments.get("refresh_cache", False)),
        )
    if name == "rag.list_documents":
        return {"documents": runtime.repo.list_documents(kb_id=arguments.get("kb_id"), limit=int(arguments.get("limit", 20)))}
    if name == "rag.submit_bad_case":
        kb_id = str(arguments.get("kb_id", ""))
        query = str(arguments.get("query", ""))
        feedback = str(arguments.get("feedback", ""))
        if not kb_id or not query or not feedback:
            raise ValueError("rag.submit_bad_case requires kb_id/query/feedback")
        return runtime.qa.record_bad_case(
            kb_id=kb_id,
            query=query,
            rewritten_query=str(arguments.get("rewritten_query", "")),
            feedback=feedback,
            retrieval_snapshot=arguments.get("retrieval_snapshot", {}) or {},
            auto_capture_snapshot=bool(arguments.get("auto_capture_snapshot", True)),
            top_k=int(arguments.get("top_k", 5)),
            candidate_multiplier=int(arguments.get("candidate_multiplier", 4)),
            fast_mode=bool(arguments.get("fast_mode", True)),
            category=str(arguments.get("category", "retrieval")),
            severity=str(arguments.get("severity", "medium")),
            status=str(arguments.get("status", "open")),
            expected_answer=str(arguments.get("expected_answer", "")),
        )
    if name == "rag.evaluate_ragas_ab":
        dataset = arguments.get("dataset", [])
        if not isinstance(dataset, list):
            raise ValueError("dataset must be a list")
        return runtime.ragas.evaluate_ab(dataset)
    if name == "rag.collection_policy":
        policy = runtime.vector_store.get_collection_policy() if hasattr(runtime.vector_store, "get_collection_policy") else {}
        managed = runtime.vector_store.list_managed_collections() if hasattr(runtime.vector_store, "list_managed_collections") else []
        return {"policy": policy, "managed_collections": managed}
    raise ValueError(f"unknown tool: {name}")


def build_mcp_app() -> FastAPI:
    """构建 MCP FastAPI 应用。"""
    app = FastAPI(title="HZ Bank RAG MCP Wrapper", version="0.1.0", description="MCP-style tool wrapper for agent integration.")
    runtime = build_runtime()

    @app.get("/health")
    def health() -> dict[str, Any]:
        return {"status": "ok", "service": "mcp-wrapper", "tools": len(_tool_specs()), "siliconflow_key_configured": bool(settings.siliconflow_api_key)}

    @app.get("/tools")
    def tools() -> dict[str, Any]:
        return {"tools": _tool_specs()}

    @app.post("/tools/call")
    def call_tool(req: ToolCallRequest) -> dict[str, Any]:
        try:
            return _call_tool(runtime, req.name, req.arguments)
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.post("/mcp")
    def mcp_rpc(req: JsonRpcRequest) -> dict[str, Any]:
        if req.jsonrpc != "2.0":
            return _err(req.id, -32600, "Invalid JSON-RPC version")
        if req.method == "initialize":
            return _ok(req.id, {"protocolVersion": "2025-03-26", "serverInfo": {"name": "hz-bank-rag-mcp", "version": "0.1.0"}, "capabilities": {"tools": {}}})
        if req.method == "tools/list":
            return _ok(req.id, {"tools": _tool_specs()})
        if req.method == "tools/call":
            name = str(req.params.get("name", ""))
            arguments = req.params.get("arguments", {})
            if not name:
                return _err(req.id, -32602, "tools/call requires name")
            if not isinstance(arguments, dict):
                return _err(req.id, -32602, "arguments must be object")
            try:
                result = _call_tool(runtime, name, arguments)
                return _ok(req.id, {"content": [{"type": "text", "text": str(result)}], "structuredContent": result})
            except Exception as exc:
                return _err(req.id, -32000, str(exc))
        return _err(req.id, -32601, f"Method not found: {req.method}")

    return app


app = build_mcp_app()


def run() -> None:
    """本地启动入口。"""
    import uvicorn
    uvicorn.run("hz_bank_rag.mcp.main:app", host="127.0.0.1", port=8091, reload=False)
