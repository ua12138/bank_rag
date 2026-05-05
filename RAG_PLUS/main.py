from __future__ import annotations

import threading
import sys
from pathlib import Path
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

try:
    from hz_bank_rag.core.config import settings as base_settings
    from hz_bank_rag.examples.seed_demo import seed_demo_data
except ModuleNotFoundError:
    project_root = Path(__file__).resolve().parents[1]
    src_dir = str(project_root / "src")
    if src_dir not in sys.path:
        sys.path.insert(0, src_dir)
    from hz_bank_rag.core.config import settings as base_settings
    from hz_bank_rag.examples.seed_demo import seed_demo_data

from RAG_PLUS.auth import AuthService, UserClaims
from RAG_PLUS.config import plus_settings
from RAG_PLUS.mcp_registry import MCPRegistry, ToolSpec
from RAG_PLUS.rag_runtime import AdaptiveQAExecutor, build_runtime
from RAG_PLUS.redis_runtime import RedisRuntime
from RAG_PLUS.router import SmartModelRouter
from RAG_PLUS.schemas import (
    PlusQueryRequest,
    TokenRequest,
    TokenResponse,
    ToolRegistrationRequest,
    ToolSearchRequest,
    WorkflowRunRequest,
)
from RAG_PLUS.workflow import MixedIntentWorkflowEngine


class LocalConcurrencyGuard:
    """本地并发舱壁，避免单实例被瞬时流量拖垮。"""

    def __init__(self, max_inflight: int) -> None:
        self._sem = threading.BoundedSemaphore(value=max(1, max_inflight))

    def acquire(self) -> bool:
        return self._sem.acquire(blocking=False)

    def release(self) -> None:
        try:
            self._sem.release()
        except ValueError:
            pass


def build_app() -> FastAPI:
    app = FastAPI(
        title="HZ Bank RAG PLUS",
        version="1.0.0",
        description="RAG_PLUS: high-concurrency architecture, smart routing, enterprise MCP registry, mixed-intent workflow.",
    )

    runtime = build_runtime()
    adaptive_qa = AdaptiveQAExecutor(runtime=runtime)
    redis_runtime = RedisRuntime()
    auth_service = AuthService()
    router = SmartModelRouter(runtime=redis_runtime)
    registry = MCPRegistry(runtime=redis_runtime)
    workflow_engine = MixedIntentWorkflowEngine()
    local_guard = LocalConcurrencyGuard(max_inflight=plus_settings.max_inflight_global)
    bearer = HTTPBearer(auto_error=False)

    def current_user(
        creds: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
    ) -> UserClaims:
        if creds is None or not creds.credentials:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="missing bearer token")
        return auth_service.token_manager.verify(creds.credentials)

    def require_scopes(claims: UserClaims, scopes: list[str]) -> None:
        AuthService.require_scopes(claims=claims, required=scopes)

    @app.get(f"{plus_settings.api_prefix}/health")
    def health() -> dict:
        return {
            "status": "ok",
            "app": plus_settings.app_name,
            "redis_enabled": redis_runtime.enabled,
            "redis_url": plus_settings.redis_url if redis_runtime.enabled else "",
            "model_pools": {
                "small": plus_settings.parse_pool(plus_settings.small_model_pool),
                "large": plus_settings.parse_pool(plus_settings.large_model_pool),
                "risky": plus_settings.parse_pool(plus_settings.risky_model_pool),
            },
            "limits": {
                "max_inflight_global": plus_settings.max_inflight_global,
                "max_inflight_per_kb": plus_settings.max_inflight_per_kb,
                "rate_limit_per_user_per_minute": plus_settings.rate_limit_per_user_per_minute,
            },
        }

    @app.post(f"{plus_settings.api_prefix}/auth/token", response_model=TokenResponse)
    def issue_token(req: TokenRequest) -> TokenResponse:
        token, scopes = auth_service.login(username=req.username, password=req.password)
        return TokenResponse(
            access_token=token,
            expires_in=plus_settings.auth_token_ttl_seconds,
            scopes=scopes,
        )

    @app.post(f"{plus_settings.api_prefix}/query")
    def plus_query(req: PlusQueryRequest, claims: Annotated[UserClaims, Depends(current_user)], request: Request) -> dict:
        require_scopes(claims, ["rag:query"])

        # 用户级限流（按分钟窗口）
        rate_key = f"user:{claims.sub}"
        if not redis_runtime.allow_rate(
            key=rate_key,
            limit=plus_settings.rate_limit_per_user_per_minute,
            window_seconds=60,
        ):
            raise HTTPException(status_code=429, detail="rate limit exceeded, please retry later")

        # 本地舱壁 + 分布式槽位，避免高并发把实例/依赖打满
        if not local_guard.acquire():
            raise HTTPException(status_code=429, detail="server is busy, local inflight limit reached")

        global_slot = redis_runtime.acquire_slot(
            bucket="global",
            max_inflight=plus_settings.max_inflight_global,
            ttl_seconds=plus_settings.inflight_slot_ttl_seconds,
        )
        kb_slot = redis_runtime.acquire_slot(
            bucket=f"kb:{req.kb_id}",
            max_inflight=plus_settings.max_inflight_per_kb,
            ttl_seconds=plus_settings.inflight_slot_ttl_seconds,
        )
        if not global_slot or not kb_slot:
            local_guard.release()
            if global_slot:
                redis_runtime.release_slot("global")
            if kb_slot:
                redis_runtime.release_slot(f"kb:{req.kb_id}")
            raise HTTPException(status_code=429, detail="server is busy, distributed inflight limit reached")

        try:
            route = router.route(req.query)
            cache_key = (
                f"q:{req.kb_id}:{redis_runtime.stable_hash(req.query)}:"
                f"{req.top_k}:{req.candidate_multiplier}:{route.selected_model}:{req.session_id}:{int(req.use_memory)}"
            )

            if not req.refresh_cache:
                cached = redis_runtime.get_json(cache_key)
                if cached is not None:
                    cached["cache_hit"] = True
                    cached["route"] = route.to_dict()
                    return cached

            result = adaptive_qa.ask(
                kb_id=req.kb_id,
                query=req.query,
                route=route,
                top_k=req.top_k,
                candidate_multiplier=req.candidate_multiplier,
                session_id=req.session_id,
                use_memory=req.use_memory,
            )
            result["cache_hit"] = False
            result["route"] = route.to_dict()
            result["request_meta"] = {
                "client": request.client.host if request.client else "",
                "user": claims.sub,
            }
            redis_runtime.set_json(cache_key, result, ttl_seconds=plus_settings.redis_cache_ttl_seconds)
            return result
        finally:
            redis_runtime.release_slot("global")
            redis_runtime.release_slot(f"kb:{req.kb_id}")
            local_guard.release()

    @app.post(f"{plus_settings.api_prefix}/mcp/tools/register")
    def register_tool(req: ToolRegistrationRequest, claims: Annotated[UserClaims, Depends(current_user)]) -> dict:
        require_scopes(claims, ["tools:write"])
        spec = ToolSpec(
            tool_id=req.tool_id,
            name=req.name,
            description=req.description,
            endpoint=req.endpoint,
            method=req.method,
            tags=req.tags,
            scopes=req.scopes,
            owner=req.owner or claims.sub,
            input_schema=req.input_schema,
            health_score=req.health_score,
            avg_latency_ms=req.avg_latency_ms,
        )
        row = registry.register(spec)
        return {"status": "ok", "tool": row.to_dict()}

    @app.get(f"{plus_settings.api_prefix}/mcp/tools")
    def list_tools(claims: Annotated[UserClaims, Depends(current_user)]) -> dict:
        require_scopes(claims, ["tools:read"])
        return {"count": len(registry.list_tools(caller_scopes=claims.scopes)), "tools": registry.list_tools(claims.scopes)}

    @app.post(f"{plus_settings.api_prefix}/mcp/tools/search")
    def search_tools(req: ToolSearchRequest, claims: Annotated[UserClaims, Depends(current_user)]) -> dict:
        require_scopes(claims, ["tools:read"])
        rows = registry.search(
            query=req.query,
            caller_scopes=claims.scopes,
            required_tags=req.required_tags,
            limit=req.limit,
        )
        return {"count": len(rows), "tools": rows}

    @app.post(f"{plus_settings.api_prefix}/workflow/run")
    def run_workflow(req: WorkflowRunRequest, claims: Annotated[UserClaims, Depends(current_user)]) -> dict:
        require_scopes(claims, ["workflow:run", "rag:query"])

        def qa_wrapper(
            kb_id: str,
            query: str,
            top_k: int,
            candidate_multiplier: int,
            session_id: str,
        ) -> dict:
            route = router.route(query)
            return adaptive_qa.ask(
                kb_id=kb_id,
                query=query,
                route=route,
                top_k=top_k,
                candidate_multiplier=candidate_multiplier,
                session_id=session_id,
                use_memory=True,
            )

        return workflow_engine.run(
            query=req.query,
            kb_id=req.kb_id,
            qa_callable=qa_wrapper,
            registry=registry,
            caller_scopes=claims.scopes,
            top_k=req.top_k,
            candidate_multiplier=req.candidate_multiplier,
            session_id=req.session_id,
        )

    @app.post(f"{plus_settings.api_prefix}/demo/seed")
    def plus_seed(claims: Annotated[UserClaims, Depends(current_user)]) -> dict:
        require_scopes(claims, ["rag:admin"])
        return seed_demo_data(repo=runtime.repo, kb_id=base_settings.default_kb_id, data_dir=Path(base_settings.data_dir))

    @app.get(f"{plus_settings.api_prefix}/mcp/snapshot")
    def mcp_snapshot(claims: Annotated[UserClaims, Depends(current_user)]) -> dict:
        require_scopes(claims, ["tools:read"])
        return registry.export_snapshot()

    return app


app = build_app()


def run() -> None:
    import uvicorn

    uvicorn.run("RAG_PLUS.main:app", host="0.0.0.0", port=8092, reload=False)
