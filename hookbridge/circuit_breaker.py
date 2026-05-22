"""Per-route circuit breaker to stop forwarding to failing destinations."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Optional


class CircuitState(str, Enum):
    CLOSED = "closed"      # normal operation
    OPEN = "open"          # blocking requests
    HALF_OPEN = "half_open"  # probing if destination recovered


@dataclass
class CircuitBreakerConfig:
    failure_threshold: int = 5        # consecutive failures before opening
    recovery_timeout: float = 30.0    # seconds before moving to HALF_OPEN
    success_threshold: int = 2        # successes in HALF_OPEN before closing


@dataclass
class BreakerState:
    state: CircuitState = CircuitState.CLOSED
    failure_count: int = 0
    success_count: int = 0
    opened_at: Optional[float] = None

    def to_dict(self) -> dict:
        return {
            "state": self.state.value,
            "failure_count": self.failure_count,
            "success_count": self.success_count,
            "opened_at": self.opened_at,
        }


class CircuitBreaker:
    def __init__(self, config: Optional[CircuitBreakerConfig] = None) -> None:
        self._config = config or CircuitBreakerConfig()
        self._routes: Dict[str, BreakerState] = {}

    def _state(self, route: str) -> BreakerState:
        if route not in self._routes:
            self._routes[route] = BreakerState()
        return self._routes[route]

    def is_allowed(self, route: str) -> bool:
        s = self._state(route)
        if s.state == CircuitState.CLOSED:
            return True
        if s.state == CircuitState.OPEN:
            if time.monotonic() - (s.opened_at or 0) >= self._config.recovery_timeout:
                s.state = CircuitState.HALF_OPEN
                s.success_count = 0
                return True
            return False
        # HALF_OPEN — allow one probe
        return True

    def record_success(self, route: str) -> None:
        s = self._state(route)
        if s.state == CircuitState.HALF_OPEN:
            s.success_count += 1
            if s.success_count >= self._config.success_threshold:
                s.state = CircuitState.CLOSED
                s.failure_count = 0
                s.opened_at = None
        elif s.state == CircuitState.CLOSED:
            s.failure_count = 0

    def record_failure(self, route: str) -> None:
        s = self._state(route)
        if s.state == CircuitState.HALF_OPEN:
            s.state = CircuitState.OPEN
            s.opened_at = time.monotonic()
            return
        s.failure_count += 1
        if s.failure_count >= self._config.failure_threshold:
            s.state = CircuitState.OPEN
            s.opened_at = time.monotonic()

    def get_state(self, route: str) -> BreakerState:
        return self._state(route)

    def all_states(self) -> Dict[str, dict]:
        return {r: s.to_dict() for r, s in self._routes.items()}

    def reset(self, route: str) -> None:
        self._routes[route] = BreakerState()
