"""In-memory event log for tracking recent webhook dispatches."""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
from collections import deque
import threading


@dataclass
class EventEntry:
    event_id: str
    route_id: str
    timestamp: str
    status: str  # 'success' | 'failure' | 'filtered'
    status_code: Optional[int]
    target_url: str
    error: Optional[str] = None
    payload_preview: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "route_id": self.route_id,
            "timestamp": self.timestamp,
            "status": self.status,
            "status_code": self.status_code,
            "target_url": self.target_url,
            "error": self.error,
            "payload_preview": self.payload_preview,
        }


class EventLog:
    def __init__(self, max_size: int = 500):
        self._max_size = max_size
        self._entries: deque = deque(maxlen=max_size)
        self._lock = threading.Lock()
        self._counter = 0

    def _next_id(self) -> str:
        self._counter += 1
        return f"evt-{self._counter:06d}"

    def record(
        self,
        route_id: str,
        status: str,
        target_url: str,
        status_code: Optional[int] = None,
        error: Optional[str] = None,
        payload_preview: Optional[str] = None,
    ) -> EventEntry:
        ts = datetime.now(timezone.utc).isoformat()
        with self._lock:
            entry = EventEntry(
                event_id=self._next_id(),
                route_id=route_id,
                timestamp=ts,
                status=status,
                status_code=status_code,
                target_url=target_url,
                error=error,
                payload_preview=payload_preview,
            )
            self._entries.append(entry)
        return entry

    def all(self) -> List[EventEntry]:
        with self._lock:
            return list(self._entries)

    def for_route(self, route_id: str) -> List[EventEntry]:
        with self._lock:
            return [e for e in self._entries if e.route_id == route_id]

    def clear(self) -> None:
        with self._lock:
            self._entries.clear()

    def size(self) -> int:
        with self._lock:
            return len(self._entries)
