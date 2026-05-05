from __future__ import annotations

"""查询缓存模块：内存版 TTL + LRU。"""

import time
from collections import OrderedDict
from dataclasses import dataclass
from typing import Any


@dataclass
class CacheEntry:
    """缓存条目。"""

    value: dict[str, Any]
    expires_at: float


class QueryCache:
    """简单内存缓存：TTL 过期 + LRU 淘汰。"""

    def __init__(self, ttl_seconds: int = 300, max_size: int = 500) -> None:
        self.ttl_seconds = max(1, ttl_seconds)
        self.max_size = max(1, max_size)
        self._data: OrderedDict[str, CacheEntry] = OrderedDict()
        self._hits = 0
        self._misses = 0

    def get(self, key: str) -> dict[str, Any] | None:
        """读取缓存，命中会刷新 LRU 顺序。"""
        now = time.time()
        entry = self._data.get(key)
        if entry is None:
            self._misses += 1
            return None
        if entry.expires_at < now:
            self._data.pop(key, None)
            self._misses += 1
            return None
        self._data.move_to_end(key, last=True)
        self._hits += 1
        return entry.value

    def set(self, key: str, value: dict[str, Any]) -> None:
        """写入缓存，并在超容量时淘汰最旧项。"""
        now = time.time()
        self._data[key] = CacheEntry(value=value, expires_at=now + self.ttl_seconds)
        self._data.move_to_end(key, last=True)
        while len(self._data) > self.max_size:
            self._data.popitem(last=False)

    def invalidate_prefix(self, prefix: str) -> None:
        """按 key 前缀批量失效。"""
        targets = [k for k in self._data.keys() if k.startswith(prefix)]
        for k in targets:
            self._data.pop(k, None)

    def stats(self) -> dict[str, Any]:
        """返回缓存统计。"""
        total = self._hits + self._misses
        hit_rate = (self._hits / total) if total else 0.0
        return {
            "enabled": True,
            "size": len(self._data),
            "max_size": self.max_size,
            "ttl_seconds": self.ttl_seconds,
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": round(hit_rate, 4),
        }
