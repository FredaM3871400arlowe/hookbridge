"""Simple in-memory response cache for idempotent webhook delivery."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from threading import Lock
from typing import Dict, Optional


@dataclass
class CacheConfig:
    ttl_seconds: float = 300.0
    max_entries: int = 1000

    def __post_init__(self) -> None:
        if self.ttl_seconds <= 0:
            raise ValueError("ttl_seconds must be positive")
        if not (1 <= self.max_entries <= 100_000):
            raise ValueError("max_entries must be between 1 and 100000")


@dataclass
class CacheEntry:
    request_id: str
    route_id: str
    status_code: int
    body: bytes
    created_at: float = field(default_factory=time.monotonic)

    def is_expired(self, ttl_seconds: float) -> bool:
        return (time.monotonic() - self.created_at) > ttl_seconds

    def to_dict(self) -> dict:
        return {
            "request_id": self.request_id,
            "route_id": self.route_id,
            "status_code": self.status_code,
            "age_seconds": round(time.monotonic() - self.created_at, 3),
        }


class ResponseCache:
    def __init__(self, config: Optional[CacheConfig] = None) -> None:
        self._config = config or CacheConfig()
        self._store: Dict[str, CacheEntry] = {}
        self._lock = Lock()

    def _key(self, request_id: str, route_id: str) -> str:
        return f"{route_id}:{request_id}"

    def get(self, request_id: str, route_id: str) -> Optional[CacheEntry]:
        key = self._key(request_id, route_id)
        with self._lock:
            entry = self._store.get(key)
            if entry is None:
                return None
            if entry.is_expired(self._config.ttl_seconds):
                del self._store[key]
                return None
            return entry

    def put(self, entry: CacheEntry) -> None:
        key = self._key(entry.request_id, entry.route_id)
        with self._lock:
            self._evict_expired()
            if len(self._store) >= self._config.max_entries:
                oldest_key = min(self._store, key=lambda k: self._store[k].created_at)
                del self._store[oldest_key]
            self._store[key] = entry

    def _evict_expired(self) -> None:
        ttl = self._config.ttl_seconds
        expired = [k for k, v in self._store.items() if v.is_expired(ttl)]
        for k in expired:
            del self._store[k]

    def size(self) -> int:
        with self._lock:
            return len(self._store)

    def clear(self) -> None:
        with self._lock:
            self._store.clear()


def config_from_dict(data: dict) -> CacheConfig:
    return CacheConfig(
        ttl_seconds=float(data.get("ttl_seconds", 300.0)),
        max_entries=int(data.get("max_entries", 1000)),
    )


def get_route_cache_config(route) -> Optional[CacheConfig]:
    raw = getattr(route, "response_cache", None)
    if not raw:
        return None
    return config_from_dict(raw)
