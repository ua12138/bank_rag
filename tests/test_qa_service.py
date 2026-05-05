from __future__ import annotations

"""QAService 单元测试：缓存、记忆压缩、家族去重。"""

from dataclasses import dataclass
from pathlib import Path

from hz_bank_rag.core.config import settings
from hz_bank_rag.core.types import RetrievalHit
from hz_bank_rag.service.qa_service import QAService
from hz_bank_rag.storage.metadata_store import MetadataStore


@dataclass
class DummyRepo:
    """最小仓储桩：只提供 `get_kb_chunk_map`。"""

    kb_chunk_map: dict[str, dict]

    def get_kb_chunk_map(self, kb_id: str, retrieval_scope: str = "active_only") -> dict[str, dict]:
        return self.kb_chunk_map


class DummyRetriever:
    """最小检索桩。"""

    def search(self, **kwargs):
        return []


class DummyRewriter:
    """最小改写桩。"""

    def rewrite(self, query: str) -> str:
        return query


class DummyReranker:
    """最小重排桩。"""

    def rerank(self, query, hits, top_k=5):
        return hits[:top_k]


def _build_service(tmp_path: Path) -> QAService:
    """构造一个可测试的 QAService（无外部依赖）。"""
    meta = MetadataStore(str(tmp_path / "qa_service.db"))
    repo = DummyRepo(
        kb_chunk_map={
            "c1": {
                "chunk_id": "c1",
                "doc_id": "d1",
                "text": "connection pool alert steps",
                "metadata": {"file_name": "ops_manual.md", "source_type": "text"},
            }
        }
    )
    return QAService(repo=repo, retriever=DummyRetriever(), rewriter=DummyRewriter(), reranker=DummyReranker(), meta=meta)


def test_query_cache_hit(tmp_path: Path, monkeypatch) -> None:
    """同请求重复调用应命中缓存，检索只执行一次。"""
    settings.enable_query_cache = True
    settings.query_cache_ttl_seconds = 300
    settings.query_cache_max_size = 20

    service = _build_service(tmp_path)
    calls = {"retrieve": 0}

    def fake_retrieve_hits(**kwargs):
        calls["retrieve"] += 1
        return [
            RetrievalHit(
                chunk_id="c1",
                doc_id="d1",
                text="connection pool alert steps",
                score=1.0,
                source="hybrid",
                metadata={"file_name": "ops_manual.md", "source_type": "text"},
            )
        ]

    monkeypatch.setattr(service, "_retrieve_hits", fake_retrieve_hits)
    monkeypatch.setattr(service, "_generate_answer", lambda **kwargs: "Do A then B")

    first = service.ask(kb_id="kb1", query="how to handle pool alert", use_memory=False)
    second = service.ask(kb_id="kb1", query="how to handle pool alert", use_memory=False)

    assert first["cache_hit"] is False
    assert second["cache_hit"] is True
    assert calls["retrieve"] == 1


def test_memory_compression(tmp_path: Path) -> None:
    """会话历史过长时应触发压缩。"""
    settings.conversation_max_turns = 2
    settings.conversation_max_chars = 80
    settings.conversation_summary_max_chars = 40

    service = _build_service(tmp_path)
    for i in range(10):
        service.meta.add_conversation_message("s1", "kb1", "user", f"user message {i} " + "x" * 50)
        service.meta.add_conversation_message("s1", "kb1", "assistant", f"assistant message {i} " + "y" * 50)

    memory_text, memory_meta = service._build_memory_context(kb_id="kb1", session_id="s1", use_memory=True)
    assert memory_meta["compressed"] is True
    assert len(memory_text) <= settings.conversation_summary_max_chars


def test_family_dedup_prefers_newest(tmp_path: Path) -> None:
    """同 family 去重时应优先保留更新版本。"""
    service = _build_service(tmp_path)
    hits = [
        RetrievalHit(
            chunk_id="c1",
            doc_id="d1",
            text="old version text",
            score=0.90,
            source="hybrid",
            metadata={"doc_family_id": "f1", "effective_at": "2025-01-01T00:00:00"},
        ),
        RetrievalHit(
            chunk_id="c2",
            doc_id="d2",
            text="new version text",
            score=0.89,
            source="hybrid",
            metadata={"doc_family_id": "f1", "effective_at": "2025-06-01T00:00:00"},
        ),
    ]
    out = service._apply_freshness_and_dedup(
        hits=hits,
        top_k=5,
        dedup_by_family=True,
        freshness_weight=0.2,
        retrieval_scope="active_only",
    )
    assert len(out) == 1
    assert out[0].doc_id == "d2"
