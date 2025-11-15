"""简单缓存封装，可选 Redis，也可回退本地内存。"""
from __future__ import annotations

import json
import os
import threading
import time
from datetime import date, datetime
from typing import Any

try:
    import redis  # type: ignore
except ImportError:  # pragma: no cover - redis 可选
    redis = None


class CacheStore:
    """提供 get/set JSON 缓存能力。"""

    def __init__(self) -> None:
        self.default_ttl = int(os.environ.get("CACHE_TTL_SECONDS", "30"))
        self._local_cache: dict[str, tuple[float, str]] = {}
        self._lock = threading.Lock()
        redis_url = os.environ.get("REDIS_URL")
        self._client = redis.from_url(redis_url, decode_responses=True) if redis_url and redis else None

    def get_json(self, key: str) -> Any | None:
        if self._client:
            payload = self._client.get(key)
            return json.loads(payload) if payload else None
        with self._lock:
            item = self._local_cache.get(key)
            if not item:
                return None
            expires_at, payload = item
            if expires_at < time.time():
                self._local_cache.pop(key, None)
                return None
            return json.loads(payload)

    def set_json(self, key: str, value: Any, ttl: int | None = None) -> None:
        ttl_to_use = ttl or self.default_ttl
        payload = json.dumps(value, default=_json_default)
        if self._client:
            self._client.setex(key, ttl_to_use, payload)
            return
        with self._lock:
            self._local_cache[key] = (time.time() + ttl_to_use, payload)

    def invalidate(self, key: str) -> None:
        if self._client:
            self._client.delete(key)
            return
        with self._lock:
            self._local_cache.pop(key, None)


cache_store = CacheStore()


def _json_default(value: Any) -> str:
    """为 datetime/date 提供默认 JSON 序列化。"""

    if isinstance(value, (datetime, date)):
        return value.isoformat()
    raise TypeError(f"Type {type(value)} not serializable")
