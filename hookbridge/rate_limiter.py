"""Rate limiting support for webhook routes."""

import time
from collections import defaultdict
from dataclasses import dataclass, field
from threading import Lock
from typing import Dict, Optional


@dataclass
class RateLimitConfig:
    requests: int
    window_seconds: int


@dataclass
class BucketState:
    count: int = 0
    window_start: float = field(default_factory=time.monotonic)


class RateLimiter:
    """Token-bucket style rate limiter keyed by route path."""

    def __init__(self) -> None:
        self._buckets: Dict[str, BucketState] = defaultdict(BucketState)
        self._lock = Lock()

    def is_allowed(
        self,
        route_path: str,
        config: RateLimitConfig,
        now: Optional[float] = None,
    ) -> bool:
        """Return True if the request is within the allowed rate, False otherwise."""
        if now is None:
            now = time.monotonic()

        with self._lock:
            bucket = self._buckets[route_path]
            elapsed = now - bucket.window_start

            if elapsed >= config.window_seconds:
                bucket.window_start = now
                bucket.count = 0

            if bucket.count < config.requests:
                bucket.count += 1
                return True

            return False

    def reset(self, route_path: str) -> None:
        """Reset the bucket for a given route (useful for testing)."""
        with self._lock:
            self._buckets.pop(route_path, None)


# Module-level singleton shared across the server lifetime
_limiter = RateLimiter()


def get_limiter() -> RateLimiter:
    return _limiter


def parse_rate_limit(route_cfg: dict) -> Optional[RateLimitConfig]:
    """Extract a RateLimitConfig from a raw route dict, or None if not configured."""
    rl = route_cfg.get("rate_limit")
    if not rl:
        return None
    return RateLimitConfig(
        requests=int(rl["requests"]),
        window_seconds=int(rl["window_seconds"]),
    )
