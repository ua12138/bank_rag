from __future__ import annotations

"""L3 答案缓存：精确 key 匹配 + 语义相似度匹配，支持按 kb_id 主动失效。"""

import copy
import threading
import time
from collections import OrderedDict
from dataclasses import dataclass
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
class _CacheEntry:
    """精确匹配缓存条目。"""
    value: dict[str, Any]
    expires_at: float


@dataclass
class _SemanticEntry:
    """语义匹配缓存条目。"""
    embedding: np.ndarray
    kb_id: str
    value: dict[str, Any]
    expires_at: float


class QueryCache:
    """L3 答案缓存：精确 key 匹配 + 语义相似度匹配。

    匹配策略：
    1. 先精确 key 匹配（O(1)）
    2. 未命中时，如果有 query_embedding，做语义相似度匹配（O(n)）
    3. 语义相似度 >= threshold 时复用缓存答案

    失效策略：
    - TTL 惰性过期
    - 按 kb_id 前缀主动失效
    - 每 50 次访问触发一次主动过期清理
    """

    def __init__(
        self,
        ttl_seconds: int = 300,
        max_size: int = 500,
        semantic_threshold: float = 0.95,
    ) -> None:
        self.ttl_seconds = max(1, ttl_seconds)
        self.max_size = max(1, max_size)
        self.semantic_threshold = semantic_threshold
        self._exact: OrderedDict[str, _CacheEntry] = OrderedDict()
        self._semantic: list[_SemanticEntry] = []
        self._lock = threading.Lock()
        self._hits = 0
        self._misses = 0
        self._access_count = 0

    def get(self, key: str, query_embedding: np.ndarray | None = None) -> dict[str, Any] | None:
        """读取缓存。先精确匹配，再语义匹配。"""
        now = time.time()
        with self._lock:
            self._access_count += 1
            if self._access_count % 50 == 0:
                self._evict_expired(now)

            # 1. 精确匹配
            entry = self._exact.get(key)
            if entry is not None:
                if entry.expires_at > now:
                    self._exact.move_to_end(key)
                    self._hits += 1
                    return copy.deepcopy(entry.value)
                self._exact.pop(key)

            # 2. 语义匹配
            if query_embedding is not None:
                best_sim = 0.0
                best_value = None
                for sem_entry in self._semantic:
                    if sem_entry.expires_at < now:
                        continue
                    sim = _cosine_similarity(query_embedding, sem_entry.embedding)
                    if sim > best_sim:
                        best_sim = sim
                        best_value = sem_entry.value
                if best_sim >= self.semantic_threshold and best_value is not None:
                    self._hits += 1
                    return copy.deepcopy(best_value)

            self._misses += 1
            return None

    def set(
        self,
        key: str,
        value: dict[str, Any],
        query_embedding: np.ndarray | None = None,
        kb_id: str = "",
    ) -> None:
        """写入缓存。同时写入精确匹配和语义匹配层。"""
        now = time.time()
        expires = now + self.ttl_seconds
        with self._lock:
            # 精确匹配层
            self._exact[key] = _CacheEntry(value=copy.deepcopy(value), expires_at=expires)
            self._exact.move_to_end(key)
            while len(self._exact) > self.max_size:
                self._exact.popitem(last=False)

            # 语义匹配层
            if query_embedding is not None:
                if len(self._semantic) >= self.max_size:
                    self._semantic.pop(0)
                self._semantic.append(_SemanticEntry(
                    embedding=query_embedding.copy(),
                    kb_id=kb_id,
                    value=copy.deepcopy(value),
                    expires_at=expires,
                ))

    def invalidate_prefix(self, prefix: str) -> None:
        """按 key 前缀批量失效精确匹配层。"""
        with self._lock:
            targets = [k for k in self._exact if k.startswith(prefix)]
            for k in targets:
                self._exact.pop(k, None)

    def invalidate_kb(self, kb_id: str) -> None:
        """按 kb_id 失效精确匹配层和语义匹配层。"""
        with self._lock:
            prefix = f"{kb_id}|"
            self._exact = OrderedDict((k, v) for k, v in self._exact.items() if not k.startswith(prefix))
            self._semantic = [e for e in self._semantic if e.kb_id != kb_id]

    def _evict_expired(self, now: float) -> None:
        """主动清理过期条目（调用时需持有锁）。"""
        expired_keys = [k for k, v in self._exact.items() if v.expires_at < now]
        for k in expired_keys:
            self._exact.pop(k, None)
        self._semantic = [e for e in self._semantic if e.expires_at >= now]

    def stats(self) -> dict[str, Any]:
        """返回缓存统计。"""
        total = self._hits + self._misses
        hit_rate = (self._hits / total) if total else 0.0
        return {
            "enabled": True,
            "layer": "L3_answer",
            "exact_size": len(self._exact),
            "semantic_size": len(self._semantic),
            "max_size": self.max_size,
            "ttl_seconds": self.ttl_seconds,
            "semantic_threshold": self.semantic_threshold,
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": round(hit_rate, 4),
        }
