from __future__ import annotations

"""L1 EmbeddingCache：文本→向量缓存，同一文本的 embedding 结果是确定性的，可永久缓存。"""

import hashlib
import threading
from collections import OrderedDict
from typing import Any

import numpy as np


class EmbeddingCache:
    """文本→向量缓存：key 是 text 的 MD5 hash，value 是向量。

    特点：
    - 永不失效（同一模型对同一文本的 embedding 是确定性的）
    - LRU 淘汰（超过 max_size 时淘汰最久未访问的）
    - 线程安全
    """

    def __init__(self, max_size: int = 10000) -> None:
        self.max_size = max(1, max_size)
        self._data: OrderedDict[str, np.ndarray] = OrderedDict()
        self._lock = threading.Lock()
        self._hits = 0
        self._misses = 0

    @staticmethod
    def _make_key(text: str) -> str:
        return hashlib.md5(text.encode("utf-8")).hexdigest()

    def get(self, text: str) -> np.ndarray | None:
        """查询缓存，命中返回向量副本，未命中返回 None。"""
        key = self._make_key(text)
        with self._lock:
            vec = self._data.get(key)
            if vec is not None:
                self._data.move_to_end(key)
                self._hits += 1
                return vec.copy()
            self._misses += 1
            return None

    def set(self, text: str, vector: np.ndarray) -> None:
        """写入缓存。超容量时淘汰最久未访问的条目。"""
        key = self._make_key(text)
        with self._lock:
            self._data[key] = vector.copy()
            self._data.move_to_end(key)
            while len(self._data) > self.max_size:
                self._data.popitem(last=False)

    def stats(self) -> dict[str, Any]:
        """返回缓存统计。"""
        total = self._hits + self._misses
        hit_rate = (self._hits / total) if total else 0.0
        return {
            "enabled": True,
            "layer": "L1_embedding",
            "size": len(self._data),
            "max_size": self.max_size,
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": round(hit_rate, 4),
        }
