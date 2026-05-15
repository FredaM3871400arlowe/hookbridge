"""Dead-letter queue: stores failed dispatch attempts for later inspection or replay."""

import json
import time
from dataclasses import dataclass, field, asdict
from typing import List, Optional


@dataclass
class DeadLetterEntry:
    route_id: str
    target_url: str
    payload: dict
    error: str
    status_code: Optional[int]
    failed_at: float = field(default_factory=time.time)
    attempt_count: int = 1

    def to_dict(self) -> dict:
        return asdict(self)


class DeadLetterQueue:
    """In-memory dead-letter queue with a configurable maximum size."""

    def __init__(self, max_size: int = 500):
        self._entries: List[DeadLetterEntry] = []
        self._max_size = max_size

    def push(self, entry: DeadLetterEntry) -> None:
        """Add a failed entry, evicting the oldest if the queue is full."""
        if len(self._entries) >= self._max_size:
            self._entries.pop(0)
        self._entries.append(entry)

    def all(self) -> List[DeadLetterEntry]:
        """Return all queued entries (oldest first)."""
        return list(self._entries)

    def for_route(self, route_id: str) -> List[DeadLetterEntry]:
        """Return entries for a specific route."""
        return [e for e in self._entries if e.route_id == route_id]

    def remove(self, route_id: str, failed_at: float) -> bool:
        """Remove a specific entry; returns True if found and removed."""
        for i, e in enumerate(self._entries):
            if e.route_id == route_id and e.failed_at == failed_at:
                self._entries.pop(i)
                return True
        return False

    def clear(self) -> None:
        self._entries.clear()

    def size(self) -> int:
        return len(self._entries)

    def to_json(self) -> str:
        return json.dumps([e.to_dict() for e in self._entries], indent=2)
