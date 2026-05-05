from __future__ import annotations

"""MetadataStore 测试：bad case 映射、会话清理、文档版本字段。"""

import json
from pathlib import Path

from hz_bank_rag.storage.metadata_store import MetadataStore


def test_bad_case_to_ragas_dataset(tmp_path: Path) -> None:
    """bad case 应可转换为 RAGAS 所需样本结构。"""
    store = MetadataStore(str(tmp_path / "meta.db"))
    snapshot = {"top_hits": [{"preview_text": "context one"}, {"preview_text": "context two"}]}
    store.add_bad_case(
        kb_id="kb1",
        query="q1",
        rewritten_query="rq1",
        feedback="bad",
        retrieval_snapshot=json.dumps(snapshot, ensure_ascii=False),
        expected_answer="ground truth",
    )

    rows = store.list_bad_case_for_ragas(kb_id="kb1", limit=10)
    assert len(rows) == 1
    assert rows[0]["question"] == "q1"
    assert rows[0]["ground_truth"] == "ground truth"
    assert rows[0]["contexts"] == ["context one", "context two"]


def test_conversation_cleanup(tmp_path: Path) -> None:
    """会话清理应只保留最近 max_keep 条。"""
    store = MetadataStore(str(tmp_path / "meta_cleanup.db"))
    for i in range(20):
        store.add_conversation_message("s1", "kb1", "user", f"u{i}")

    deleted = store.delete_conversation_messages_before("s1", "kb1", max_keep=5)
    assert deleted >= 15

    remain = store.get_conversation_messages("s1", "kb1", limit=50)
    assert len(remain) == 5
    assert remain[0]["content"] == "u15"
    assert remain[-1]["content"] == "u19"


def test_document_version_fields(tmp_path: Path) -> None:
    """文档版本相关字段应正确落库并可读取。"""
    store = MetadataStore(str(tmp_path / "meta_doc.db"))
    store.ensure_knowledge_base("kb1")
    store.add_document(
        doc_id="d1",
        kb_id="kb1",
        file_path="a.md",
        parser_type="text",
        file_hash="h1",
        content_hash="h1",
        near_hash="n1",
        file_size=10,
        doc_family_id="fam-a",
        version_no=2,
        effective_at="2025-05-01T00:00:00",
        is_active=True,
        keywords=["交易系统", "告警"],
    )
    row = store.get_document("d1")
    assert row is not None
    assert row["doc_family_id"] == "fam-a"
    assert row["version_no"] == 2
    assert row["is_active"] is True
    assert "交易系统" in row["keywords"]
