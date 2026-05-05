from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient

from hz_bank_rag.api.main import build_app
from hz_bank_rag.core.config import settings


def _record_step(steps: list[dict[str, Any]], name: str, ok: bool, detail: dict[str, Any] | None = None) -> None:
    steps.append({"name": name, "ok": ok, "detail": detail or {}})


def run_regression(kb_id: str, query: str) -> dict[str, Any]:
    app = build_app()
    client = TestClient(app)

    steps: list[dict[str, Any]] = []

    health = client.get("/health")
    _record_step(steps, "health", health.status_code == 200, {"status_code": health.status_code, "body": health.json()})

    seed = client.post("/demo/seed")
    seed_ok = seed.status_code == 200 and seed.json().get("count", 0) > 0
    _record_step(steps, "seed", seed_ok, {"status_code": seed.status_code, "body": seed.json()})

    query_resp = client.post(
        "/query",
        json={
            "kb_id": kb_id,
            "query": query,
            "fast_mode": True,
            "session_id": "regression-session",
            "use_memory": True,
            "refresh_cache": True,
        },
    )
    query_body = query_resp.json()
    query_ok = query_resp.status_code == 200 and bool(query_body.get("answer", "").strip())
    _record_step(
        steps,
        "query",
        query_ok,
        {
            "status_code": query_resp.status_code,
            "answer_preview": query_body.get("answer", "")[:200],
            "citations": len(query_body.get("citations", [])),
            "cache_hit": query_body.get("cache_hit", False),
            "latency_ms": query_body.get("latency_ms"),
        },
    )

    try:
        bad_case_resp = client.post(
            "/bad-cases",
            json={
                "kb_id": kb_id,
                "query": query,
                "feedback": "Regression run auto bad-case sample",
                "category": "retrieval",
                "severity": "low",
                "status": "open",
                "expected_answer": "Sample expected answer for regression",
                "auto_capture_snapshot": True,
            },
        )
        bad_case_body = bad_case_resp.json()
        bad_case_ok = bad_case_resp.status_code == 200 and bad_case_body.get("status") == "ok"
        _record_step(steps, "bad_case", bad_case_ok, {"status_code": bad_case_resp.status_code, "body": bad_case_body})
    except Exception as exc:
        bad_case_body = {"error": str(exc)}
        _record_step(steps, "bad_case", False, {"exception": str(exc)})

    try:
        ragas_dataset_resp = client.get("/bad-cases/ragas-dataset", params={"kb_id": kb_id, "limit": 20, "fill_answer": True})
        ragas_dataset_body = ragas_dataset_resp.json()
        ragas_dataset_ok = ragas_dataset_resp.status_code == 200 and ragas_dataset_body.get("rows", 0) > 0
        _record_step(
            steps,
            "bad_case_to_ragas_dataset",
            ragas_dataset_ok,
            {
                "status_code": ragas_dataset_resp.status_code,
                "rows": ragas_dataset_body.get("rows", 0),
            },
        )
    except Exception as exc:
        ragas_dataset_body = {"dataset": []}
        _record_step(steps, "bad_case_to_ragas_dataset", False, {"exception": str(exc)})

    dataset = ragas_dataset_body.get("dataset", [])[:5]
    ragas_light_resp = None
    ragas_official_resp = None
    ragas_ab_resp = None
    if dataset:
        try:
            ragas_light_resp = client.post("/evaluate/ragas", json={"dataset": dataset})
        except Exception:
            ragas_light_resp = None
        try:
            ragas_official_resp = client.post("/evaluate/ragas/official", json={"dataset": dataset})
        except Exception:
            ragas_official_resp = None
        try:
            ragas_ab_resp = client.post("/evaluate/ragas/ab", json={"dataset": dataset})
        except Exception:
            ragas_ab_resp = None

    if dataset and ragas_light_resp is not None:
        _record_step(steps, "ragas_lightweight", ragas_light_resp.status_code == 200, {"status_code": ragas_light_resp.status_code, "body": ragas_light_resp.json()})
    else:
        _record_step(steps, "ragas_lightweight", False, {"reason": "dataset is empty"})

    if dataset and ragas_official_resp is not None:
        _record_step(steps, "ragas_official", ragas_official_resp.status_code == 200, {"status_code": ragas_official_resp.status_code, "body": ragas_official_resp.json()})
    else:
        _record_step(steps, "ragas_official", False, {"reason": "dataset is empty"})

    if dataset and ragas_ab_resp is not None:
        _record_step(steps, "ragas_ab", ragas_ab_resp.status_code == 200, {"status_code": ragas_ab_resp.status_code, "body": ragas_ab_resp.json()})
    else:
        _record_step(steps, "ragas_ab", False, {"reason": "dataset is empty"})

    conversation = client.get(f"/conversations/regression-session", params={"kb_id": kb_id, "limit": 20})
    _record_step(
        steps,
        "conversation_memory",
        conversation.status_code == 200,
        {"status_code": conversation.status_code, "messages": len(conversation.json().get("messages", []))},
    )

    policy = client.get("/collections/policy")
    _record_step(steps, "collection_policy", policy.status_code == 200, {"status_code": policy.status_code, "body": policy.json()})

    managed = client.get("/collections/managed")
    _record_step(steps, "collection_list", managed.status_code == 200, {"status_code": managed.status_code, "body": managed.json()})

    cleanup = client.post("/collections/cleanup", params={"dry_run": True})
    _record_step(steps, "collection_cleanup_dry_run", cleanup.status_code == 200, {"status_code": cleanup.status_code, "body": cleanup.json()})

    passed = [s for s in steps if s["ok"]]
    failed = [s for s in steps if not s["ok"]]

    return {
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "kb_id": kb_id,
        "query": query,
        "settings": {
            "use_milvus": settings.use_milvus,
            "milvus_uri": settings.milvus_uri,
            "cache_enabled": settings.enable_query_cache,
            "conversation_max_turns": settings.conversation_max_turns,
        },
        "summary": {
            "total_steps": len(steps),
            "passed": len(passed),
            "failed": len(failed),
            "status": "pass" if not failed else "partial",
        },
        "steps": steps,
    }


def _write_report(report: dict[str, Any], out_dir: Path) -> tuple[Path, Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    json_path = out_dir / f"regression_report_{stamp}.json"
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    md_path = out_dir / f"regression_report_{stamp}.md"
    lines = [
        "# Regression Report",
        "",
        f"- Timestamp: {report['timestamp']}",
        f"- KB: {report['kb_id']}",
        f"- Query: {report['query']}",
        f"- Status: {report['summary']['status']}",
        f"- Passed/Total: {report['summary']['passed']}/{report['summary']['total_steps']}",
        "",
        "## Steps",
    ]
    for step in report["steps"]:
        mark = "PASS" if step["ok"] else "FAIL"
        lines.append(f"- [{mark}] {step['name']}")
    lines.append("")
    md_path.write_text("\n".join(lines), encoding="utf-8")

    return json_path, md_path


def main() -> int:
    parser = argparse.ArgumentParser(description="Run end-to-end regression for hz_bank_rag")
    parser.add_argument("--kb-id", default=settings.default_kb_id)
    parser.add_argument("--query", default="How to handle database connection pool alerts?")
    parser.add_argument("--out-dir", default="reports")
    args = parser.parse_args()

    report = run_regression(kb_id=args.kb_id, query=args.query)
    json_path, md_path = _write_report(report, Path(args.out_dir))

    print(f"Regression report JSON: {json_path}")
    print(f"Regression report MD  : {md_path}")
    print(f"Summary: {report['summary']}")
    return 0 if report["summary"]["failed"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
