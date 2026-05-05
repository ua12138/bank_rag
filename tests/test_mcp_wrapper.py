from __future__ import annotations

"""MCP 包装层测试：工具列表与 JSON-RPC 基础行为。"""

from fastapi.testclient import TestClient

from hz_bank_rag.mcp.main import build_mcp_app


def test_mcp_tools_list() -> None:
    """`/tools` 应返回工具清单，且包含 rag.query。"""
    app = build_mcp_app()
    client = TestClient(app)

    resp = client.get("/tools")
    assert resp.status_code == 200
    body = resp.json()
    assert "tools" in body
    assert any(tool.get("name") == "rag.query" for tool in body["tools"])


def test_mcp_jsonrpc_initialize_and_health_tool() -> None:
    """JSON-RPC initialize 与 tools/call(rag.health) 应成功。"""
    app = build_mcp_app()
    client = TestClient(app)

    init_resp = client.post(
        "/mcp",
        json={"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}},
    )
    assert init_resp.status_code == 200
    assert init_resp.json().get("result", {}).get("serverInfo", {}).get("name") == "hz-bank-rag-mcp"

    call_resp = client.post(
        "/mcp",
        json={
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/call",
            "params": {"name": "rag.health", "arguments": {}},
        },
    )
    assert call_resp.status_code == 200
    result = call_resp.json().get("result", {})
    assert "structuredContent" in result
    assert result["structuredContent"].get("status") == "ok"
