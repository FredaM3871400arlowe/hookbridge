"""Simple in-memory metrics collector for hookbridge."""

import time
from collections import defaultdict
from dataclasses import dataclass, field
from threading import Lock
from typing import Dict, List


@dataclass
class RouteMetrics:
    route_id: str
    total_dispatched: int = 0
    total_success: int = 0
    total_failed: int = 0
    total_filtered: int = 0
    last_dispatched_at: float = 0.0
    latencies_ms: List[float] = field(default_factory=list)

    def avg_latency_ms(self) -> float:
        if not self.latencies_ms:
            return 0.0
        return sum(self.latencies_ms) / len(self.latencies_ms)

    def to_dict(self) -> dict:
        return {
            "route_id": self.route_id,
            "total_dispatched": self.total_dispatched,
            "total_success": self.total_success,
            "total_failed": self.total_failed,
            "total_filtered": self.total_filtered,
            "last_dispatched_at": self.last_dispatched_at,
            "avg_latency_ms": round(self.avg_latency_ms(), 3),
        }


class MetricsCollector:
    def __init__(self) -> None:
        self._lock = Lock()
        self._routes: Dict[str, RouteMetrics] = defaultdict(
            lambda: RouteMetrics(route_id="")
        )

    def _get(self, route_id: str) -> RouteMetrics:
        if route_id not in self._routes:
            self._routes[route_id] = RouteMetrics(route_id=route_id)
        return self._routes[route_id]

    def record_dispatch(self, route_id: str, success: bool, latency_ms: float) -> None:
        with self._lock:
            m = self._get(route_id)
            m.total_dispatched += 1
            m.last_dispatched_at = time.time()
            m.latencies_ms = m.latencies_ms[-99:]  # keep last 100
            m.latencies_ms.append(latency_ms)
            if success:
                m.total_success += 1
            else:
                m.total_failed += 1

    def record_filtered(self, route_id: str) -> None:
        with self._lock:
            self._get(route_id).total_filtered += 1

    def snapshot(self) -> List[dict]:
        with self._lock:
            return [m.to_dict() for m in self._routes.values()]

    def reset(self) -> None:
        with self._lock:
            self._routes.clear()


# Module-level singleton
_collector = MetricsCollector()


def get_collector() -> MetricsCollector:
    return _collector
