from __future__ import annotations

import hashlib
import json
import threading
import time
from typing import Any

from RAG_PLUS.config import plus_settings

try:
    import redis  # type: ignore
except Exception:  # pragma: no cover
    redis = None


class RedisRuntime:
    """
    Redis 运行时封装：
    1) 查询缓存
    2) 限流计数
    3) 并发槽位控制（简单分布式回压）
    4) 模型池轮询（负载均衡）
    """

    def __init__(self) -> None:
        self.enabled = bool(plus_settings.redis_enabled and redis is not None)
        self.prefix = plus_settings.redis_prefix
        self._client = None
        self._lock = threading.Lock()

        # 本地降级存储
        self._local_cache: dict[str, tuple[float, Any]] = {}
        self._local_counter: dict[str, tuple[int, float]] = {}
        self._local_rr: dict[str, int] = {}
        self._local_slot: dict[str, int] = {}

        if self.enabled:
            try:
                self._client = redis.Redis.from_url(plus_settings.redis_url, decode_responses=True)
                self._client.ping()
            except Exception:
                self.enabled = False
                self._client = None

    def _k(self, name: str) -> str:
        return f"{self.prefix}:{name}"

    @staticmethod
    def stable_hash(text: str) -> str:
        return hashlib.sha1(text.encode("utf-8")).hexdigest()

    def get_json(self, key: str) -> dict[str, Any] | None:
        if self.enabled and self._client is not None:
            val = self._client.get(self._k(key))
            if not val:
                return None
            try:
                return json.loads(val)
            except Exception:
                return None

        now = time.time()
        with self._lock:
            row = self._local_cache.get(key)
            if row is None:
                return None
            exp, val = row
            if exp < now:
                self._local_cache.pop(key, None)
                return None
            return val

    def set_json(self, key: str, value: dict[str, Any], ttl_seconds: int) -> None:
        if self.enabled and self._client is not None:
            self._client.setex(self._k(key), max(1, ttl_seconds), json.dumps(value, ensure_ascii=False))
            return

        with self._lock:
            self._local_cache[key] = (time.time() + max(1, ttl_seconds), value)

    def allow_rate(self, key: str, limit: int, window_seconds: int) -> bool:
        if limit <= 0:
            return True

        if self.enabled and self._client is not None:
            full_key = self._k(f"rl:{key}:{int(time.time() // window_seconds)}")
            value = self._client.incr(full_key)
            if value == 1:
                self._client.expire(full_key, max(1, window_seconds))
            return int(value) <= limit

        now_bucket = int(time.time() // window_seconds)
        local_key = f"{key}:{now_bucket}"
        with self._lock:
            count, exp = self._local_counter.get(local_key, (0, time.time() + window_seconds))
            if time.time() > exp:
                count = 0
                exp = time.time() + window_seconds
            count += 1
            self._local_counter[local_key] = (count, exp)
            return count <= limit

    def acquire_slot(self, bucket: str, max_inflight: int, ttl_seconds: int) -> bool:
        if max_inflight <= 0:
            return True

        if self.enabled and self._client is not None:
            key = self._k(f"slot:{bucket}")
            value = self._client.incr(key)
            if value == 1:
                self._client.expire(key, max(1, ttl_seconds))
            if int(value) > max_inflight:
                self._client.decr(key)
                return False
            return True

        with self._lock:
            used = self._local_slot.get(bucket, 0)
            if used >= max_inflight:
                return False
            self._local_slot[bucket] = used + 1
            return True

    def release_slot(self, bucket: str) -> None:
        if self.enabled and self._client is not None:
            key = self._k(f"slot:{bucket}")
            try:
                self._client.decr(key)
            except Exception:
                pass
            return

        with self._lock:
            used = self._local_slot.get(bucket, 0)
            if used <= 1:
                self._local_slot.pop(bucket, None)
            else:
                self._local_slot[bucket] = used - 1

    def select_from_pool(self, name: str, pool: list[str]) -> str:
        if not pool:
            return ""
        if len(pool) == 1:
            return pool[0]

        if self.enabled and self._client is not None:
            key = self._k(f"rr:{name}")
            idx = int(self._client.incr(key))
            return pool[(idx - 1) % len(pool)]

        with self._lock:
            idx = self._local_rr.get(name, 0)
            self._local_rr[name] = idx + 1
            return pool[idx % len(pool)]

