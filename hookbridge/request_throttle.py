"""Per-route request throttling (concurrent request cap)."""

from __future__ import annotations

import threading
from dataclasses import dataclass, field
from typing import Dict, Optional


@dataclass
class ThrottleConfig:
    max_concurrent: int = 10

    def __post_init__(self) -> None:
        if self.max_concurrent < 1:
            raise ValueError("max_concurrent must be at least 1")
        if self.max_concurrent > 1000:
            raise ValueError("max_concurrent must not exceed 1000")


@dataclass
class ThrottleState:
    config: ThrottleConfig
    _active: int = field(default=0, init=False)
    _lock: threading.Lock = field(default_factory=threading.Lock, init=False)

    def acquire(self) -> bool:
        """Try to acquire a slot. Returns True if allowed, False if at capacity."""
        with self._lock:
            if self._active >= self.config.max_concurrent:
                return False
            self._active += 1
            return True

    def release(self) -> None:
        """Release a previously acquired slot."""
        with self._lock:
            if self._active > 0:
                self._active -= 1

    @property
    def active(self) -> int:
        with self._lock:
            return self._active

    def to_dict(self) -> dict:
        return {
            "max_concurrent": self.config.max_concurrent,
            "active": self.active,
            "available": self.config.max_concurrent - self.active,
        }


_states: Dict[str, ThrottleState] = {}
_global_lock = threading.Lock()


def config_from_dict(data: dict) -> ThrottleConfig:
    return ThrottleConfig(max_concurrent=int(data.get("max_concurrent", 10)))


def get_route_throttle(route: object) -> Optional[ThrottleConfig]:
    cfg = getattr(route, "throttle", None)
    if cfg is None:
        return None
    return config_from_dict(cfg) if isinstance(cfg, dict) else cfg


def get_state(route_id: str, config: ThrottleConfig) -> ThrottleState:
    with _global_lock:
        if route_id not in _states:
            _states[route_id] = ThrottleState(config=config)
        return _states[route_id]


def check_throttle_for_route(route_id: str, route: object) -> Optional[dict]:
    """Returns an error dict if throttled, else None."""
    cfg = get_route_throttle(route)
    if cfg is None:
        return None
    state = get_state(route_id, cfg)
    if not state.acquire():
        return {
            "status": 429,
            "error": "Too Many Concurrent Requests",
            "detail": f"Max concurrent requests ({cfg.max_concurrent}) reached for route '{route_id}'.",
        }
    return None


def release_throttle(route_id: str) -> None:
    """Release a throttle slot for the given route if one exists."""
    with _global_lock:
        state = _states.get(route_id)
    if state:
        state.release()
