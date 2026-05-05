from __future__ import annotations

"""核心类型定义：统一项目中的数据结构。"""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class Chunk:
    """标准化分块记录（用于存储与检索）。"""

    chunk_id: str
    kb_id: str
    doc_id: str
    text: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class RetrievalHit:
    """统一检索命中结构（稀疏 + 稠密 + 重排阶段复用）。"""

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
