from __future__ import annotations

import json
import re
import threading
from dataclasses import asdict, dataclass, field
from typing import Any

from RAG_PLUS.redis_runtime import RedisRuntime


@dataclass
class ToolSpec:
    tool_id: str
    name: str
    description: str
    endpoint: str
    method: str = "POST"
    tags: list[str] = field(default_factory=list)
    scopes: list[str] = field(default_factory=lambda: ["tools:read"])
    owner: str = ""
    input_schema: dict[str, Any] = field(default_factory=dict)
    health_score: float = 1.0
    avg_latency_ms: int = 100

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class MCPRegistry:
    """
    企业级 MCP 工具注册中心（轻量实现）：
    - 注册工具
    - 条件过滤与语义近似检索
    - 基于 scope 的可见性控制
    """

    def __init__(self, runtime: RedisRuntime) -> None:
        self.runtime = runtime
        self._tools: dict[str, ToolSpec] = {}
        self._lock = threading.Lock()

    def register(self, spec: ToolSpec) -> ToolSpec:
        with self._lock:
            self._tools[spec.tool_id] = spec
        self.runtime.set_json(
            key=f"mcp:tool:{spec.tool_id}",
            value=spec.to_dict(),
            ttl_seconds=86400 * 30,
        )
        return spec

    def list_tools(self, caller_scopes: list[str]) -> list[dict[str, Any]]:
        visible: list[dict[str, Any]] = []
        with self._lock:
            for spec in self._tools.values():
                if self._allowed(caller_scopes, spec.scopes):
                    visible.append(spec.to_dict())
        return sorted(visible, key=lambda x: x["tool_id"])

    def search(
        self,
        query: str,
        caller_scopes: list[str],
        required_tags: list[str] | None = None,
        limit: int = 8,
    ) -> list[dict[str, Any]]:
        q_tokens = self._tokens(query)
        tags = set([x.lower() for x in (required_tags or [])])
        rows: list[tuple[float, ToolSpec]] = []

        with self._lock:
            specs = list(self._tools.values())

        for spec in specs:
            if not self._allowed(caller_scopes, spec.scopes):
                continue
            if tags and not tags.issubset(set([t.lower() for t in spec.tags])):
                continue

            text = f"{spec.name} {spec.description} {' '.join(spec.tags)}".lower()
            score = 0.0

            for tok in q_tokens:
                if tok in text:
                    score += 1.8

            # 结合稳定性做重排：健康度越高、时延越低优先
            score += spec.health_score * 1.5
            score += 1.0 / max(1, spec.avg_latency_ms / 50)
            rows.append((score, spec))

        rows.sort(key=lambda x: x[0], reverse=True)
        return [
            {
                "score": round(score, 4),
                **spec.to_dict(),
            }
            for score, spec in rows[: max(1, limit)]
        ]

    @staticmethod
    def _allowed(caller_scopes: list[str], required_scopes: list[str]) -> bool:
        caller = set(caller_scopes)
        return all(scope in caller or "rag:admin" in caller for scope in required_scopes)

    @staticmethod
    def _tokens(text: str) -> list[str]:
        txt = (text or "").lower()
        parts = re.split(r"[\s,，。；;:：\n\t]+", txt)
        return [p for p in parts if p]

    def export_snapshot(self) -> dict[str, Any]:
        with self._lock:
            data = [tool.to_dict() for tool in self._tools.values()]
        return {"count": len(data), "tools": data}

    def import_snapshot(self, payload: dict[str, Any]) -> int:
        rows = payload.get("tools", [])
        loaded = 0
        with self._lock:
            for row in rows:
                try:
                    spec = ToolSpec(**json.loads(json.dumps(row, ensure_ascii=False)))
                except Exception:
                    continue
                self._tools[spec.tool_id] = spec
                loaded += 1
        return loaded

