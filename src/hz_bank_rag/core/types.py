from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class Chunk:
    """A normalized chunk record for storage/retrieval."""

    chunk_id: str
    kb_id: str
    doc_id: str
    text: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class RetrievalHit:
    """Unified retrieval hit for sparse+dense+rerank stages."""

    chunk_id: str
    doc_id: str
    text: str
    score: float
    source: str
    bm25_score: float = 0.0
    vector_score: float = 0.0
    rrf_score: float = 0.0
    rerank_score: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)
