"""Request deduplication middleware using a sliding window cache of request IDs."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Dict, Optional, Tuple


_DEFAULT_WINDOW_SECONDS = 300  # 5 minutes
_DEFAULT_MAX_ENTRIES = 10_000


@dataclass
class DedupConfig:
    window_seconds: int = _DEFAULT_WINDOW_SECONDS
    max_entries: int = _DEFAULT_MAX_ENTRIES

    def __post_init__(self) -> None:
        if self.window_seconds < 1:
            raise ValueError("window_seconds must be >= 1")
        if self.window_seconds > 86_400:
            raise ValueError("window_seconds must be <= 86400")
        if self.max_entries < 1:
            raise ValueError("max_entries must be >= 1")
        if self.max_entries > 100_000:
            raise ValueError("max_entries must be <= 100000")


def config_from_dict(data: dict) -> DedupConfig:
    """Build a DedupConfig from a plain dict (e.g. from route config)."""
    return DedupConfig(
        window_seconds=int(data.get("window_seconds", _DEFAULT_WINDOW_SECONDS)),
        max_entries=int(data.get("max_entries", _DEFAULT_MAX_ENTRIES)),
    )


class RequestDeduplicator:
    """Tracks seen request IDs within a rolling time window."""

    def __init__(self, config: DedupConfig) -> None:
        self._config = config
        # Maps request_id -> timestamp of first receipt
        self._seen: Dict[str, float] = {}

    def is_duplicate(self, request_id: str) -> bool:
        """Return True if request_id was already seen within the window."""
        self._evict_expired()
        return request_id in self._seen

    def record(self, request_id: str) -> None:
        """Record a new request_id. Evicts oldest entry if at capacity."""
        self._evict_expired()
        if len(self._seen) >= self._config.max_entries:
            # Remove the oldest entry
            oldest = min(self._seen, key=lambda k: self._seen[k])
            del self._seen[oldest]
        self._seen[request_id] = time.monotonic()

    def size(self) -> int:
        self._evict_expired()
        return len(self._seen)

    def _evict_expired(self) -> None:
        cutoff = time.monotonic() - self._config.window_seconds
        expired = [k for k, ts in self._seen.items() if ts < cutoff]
        for k in expired:
            del self._seen[k]


# Per-route registry keyed by route id
_dedup_registry: Dict[str, RequestDeduplicator] = {}


def get_deduplicator(route_id: str, config: DedupConfig) -> RequestDeduplicator:
    """Return (or create) the deduplicator for a given route."""
    if route_id not in _dedup_registry:
        _dedup_registry[route_id] = RequestDeduplicator(config)
    return _dedup_registry[route_id]


def get_route_dedup_config(route: object) -> Optional[DedupConfig]:
    """Extract DedupConfig from a RouteConfig, or None if not configured."""
    raw = getattr(route, "dedup", None)
    if raw is None:
        return None
    return config_from_dict(raw if isinstance(raw, dict) else {})


def check_dedup_for_route(
    route: object, request_id: Optional[str]
) -> Tuple[bool, Optional[DedupConfig]]:
    """Return (is_duplicate, config). is_duplicate is False if dedup not configured."""
    cfg = get_route_dedup_config(route)
    if cfg is None or not request_id:
        return False, cfg
    route_id = getattr(route, "id", str(route))
    dedup = get_deduplicator(route_id, cfg)
    if dedup.is_duplicate(request_id):
        return True, cfg
    dedup.record(request_id)
    return False, cfg


def build_dedup_response(request_id: str) -> dict:
    """Build a JSON-serialisable rejection payload for duplicate requests."""
    return {
        "error": "duplicate_request",
        "request_id": request_id,
        "message": "A request with this ID has already been processed.",
    }
