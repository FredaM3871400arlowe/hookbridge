"""In-memory event log for recording webhook dispatch activity."""

import threading
from dataclasses import dataclass, field
from typing import List, Optional
import time


@dataclass
class EventEntry:
    event_id: int
    route: str
    status: str          # "success" | "failure" | "filtered"
    target_url: str
    http_status: Optional[int]
    error: Optional[str]
    timestamp: float = field(default_factory=time.time)

    def to_dict(self):
        return {
            "event_id": self.event_id,
            "route": self.route,
            "status": self.status,
            "target_url": self.target_url,
            "http_status": self.http_status,
            "error": self.error,
            "timestamp": self.timestamp,
        }


class EventLog:
    def __init__(self, max_size: int = 1000):
        self._entries: List[EventEntry] = []
        self._lock = threading.Lock()
        self._max_size = max_size
        self._counter = 0

    def _next_id(self) -> int:
        self._counter += 1
        return self._counter

    def record(
        self,
        route: str,
        status: str,
        target_url: str,
        http_status: Optional[int] = None,
        error: Optional[str] = None,
    ) -> EventEntry:
        with self._lock:
            entry = EventEntry(
                event_id=self._next_id(),
                route=route,
                status=status,
                target_url=target_url,
                http_status=http_status,
                error=error,
            )
            self._entries.append(entry)
            if len(self._entries) > self._max_size:
                self._entries.pop(0)
            return entry

    def all(self) -> List[EventEntry]:
        with self._lock:
            return list(self._entries)

    def for_route(self, route: str) -> List[EventEntry]:
        with self._lock:
            return [e for e in self._entries if e.route == route]

    def get(self, event_id: int) -> Optional[EventEntry]:
        with self._lock:
            for e in self._entries:
                if e.event_id == event_id:
                    return e
        return None

    def clear(self):
        with self._lock:
            self._entries.clear()
            self._counter = 0

    def size(self) -> int:
        with self._lock:
            return len(self._entries)
