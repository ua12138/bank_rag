from __future__ import annotations

"""L2 RetrievalCache：检索结果语义缓存，用 embedding 相似度匹配已缓存的检索结果。"""

import copy
import threading
import time
from dataclasses import dataclass, field
from typing import Any

import numpy as np


def _cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    """计算两个向量的余弦相似度。"""
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return float(np.dot(a, b) / (norm_a * norm_b))


@dataclass
class _RetrievalEntry:
    """单条缓存条目。"""
    embedding: np.ndarray
    kb_id: str
    params_hash: str
    hits: list
    expires_at: float


@dataclass
class _CacheStats:
    """缓存统计。"""
    hits: int = 0
    misses: int = 0


class RetrievalCache:
    """检索结果语义缓存。

    原理：对 query 做 embedding 后，用余弦相似度匹配已缓存的 query。
    当相似度 >= threshold 时，复用缓存的检索结果，跳过整个检索流程。

    特点：
    - 语义相似的 query 可以命中（如"数据库连接池超时" ≈ "DB连接池配置问题"）
    - TTL 过期
    - 按 kb_id 主动失效
    - 线程安全
    """

    def __init__(
        self,
        ttl_seconds: int = 180,
        max_size: int = 200,
        similarity_threshold: float = 0.92,
    ) -> None:
        self.ttl_seconds = max(1, ttl_seconds)
        self.max_size = max(1, max_size)
        self.similarity_threshold = similarity_threshold
        self._entries: list[_RetrievalEntry] = []
        self._lock = threading.Lock()
        self._stats = _CacheStats()

    def get(self, query_embedding: np.ndarray, kb_id: str, params_hash: str) -> list | None:
        """用余弦相似度查找最相似的已缓存检索结果。"""
        now = time.time()
        with self._lock:
            best_sim = 0.0
            best_hits = None
            for entry in self._entries:
                if entry.expires_at < now or entry.kb_id != kb_id or entry.params_hash != params_hash:
                    continue
                sim = _cosine_similarity(query_embedding, entry.embedding)
                if sim > best_sim:
                    best_sim = sim
                    best_hits = entry.hits
            if best_sim >= self.similarity_threshold and best_hits is not None:
                self._stats.hits += 1
                return copy.deepcopy(best_hits)
            self._stats.misses += 1
            return None

    def set(self, query_embedding: np.ndarray, kb_id: str, params_hash: str, hits: list) -> None:
        """写入缓存。超容量时淘汰最旧条目。"""
        with self._lock:
            if len(self._entries) >= self.max_size:
                self._entries.pop(0)
            self._entries.append(_RetrievalEntry(
                embedding=query_embedding.copy(),
                kb_id=kb_id,
                params_hash=params_hash,
                hits=copy.deepcopy(hits),
                expires_at=time.time() + self.ttl_seconds,
            ))

    def invalidate_kb(self, kb_id: str) -> None:
        """按 kb_id 失效所有相关缓存。"""
        with self._lock:
            self._entries = [e for e in self._entries if e.kb_id != kb_id]

    def stats(self) -> dict[str, Any]:
        """返回缓存统计。"""
        total = self._stats.hits + self._stats.misses
        hit_rate = (self._stats.hits / total) if total else 0.0
        return {
            "enabled": True,
            "layer": "L2_retrieval",
            "size": len(self._entries),
            "max_size": self.max_size,
            "ttl_seconds": self.ttl_seconds,
            "similarity_threshold": self.similarity_threshold,
            "hits": self._stats.hits,
            "misses": self._stats.misses,
            "hit_rate": round(hit_rate, 4),
        }
