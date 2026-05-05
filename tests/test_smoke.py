from __future__ import annotations

"""烟雾测试：验证服务基础可用与最小端到端流程。"""

import json
import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from hz_bank_rag.api.main import build_app
from hz_bank_rag.core.config import settings


def test_health(tmp_path: Path) -> None:
    """健康检查接口应返回 200 且 status=ok。"""
    settings.use_milvus = False
    settings.sqlite_path = str(tmp_path / "test_health.db")
    app = build_app()
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_end_to_end_flow(tmp_path: Path) -> None:
    """最小端到端：seed -> query -> evaluate。"""
    if not (settings.siliconflow_api_key or os.getenv("HZ_RAG_SILICONFLOW_API_KEY")):
        pytest.skip("HZ_RAG_SILICONFLOW_API_KEY is not configured")

    settings.use_milvus = False
    settings.sqlite_path = str(tmp_path / "test_flow.db")
    settings.data_dir = str((Path("data") / "demo_kb").resolve())
    settings.default_kb_id = "demo-kb-test"
    app = build_app()
    client = TestClient(app)

    seed_response = client.post("/demo/seed")
    assert seed_response.status_code == 200
    assert seed_response.json()["count"] >= 1

    query_response = client.post(
        "/query",
        json={
            "kb_id": settings.default_kb_id,
            "query": "How to handle database connection pool alert?",
            "top_k": 3,
            "candidate_multiplier": 3,
            "fast_mode": True,
        },
    )
    assert query_response.status_code == 200
    payload = query_response.json()
    assert payload["citations"]
    assert isinstance(payload["answer"], str)
    assert payload["answer"].strip()

    ragas_dataset = json.loads((Path("data") / "eval_samples" / "ragas_eval.json").read_text(encoding="utf-8-sig"))
    eval_response = client.post("/evaluate/ragas", json={"dataset": ragas_dataset})
    assert eval_response.status_code == 200
    assert eval_response.json()["status"] in {"ok", "partial", "error"}
