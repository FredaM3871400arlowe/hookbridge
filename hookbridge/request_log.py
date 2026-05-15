"""Incoming request logging: records raw inbound webhook requests per route."""

import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class RequestEntry:
    request_id: int
    route: str
    method: str
    headers: Dict[str, str]
    payload: Any
    source_ip: str
    timestamp: float = field(default_factory=time.time)
    status_code: Optional[int] = None  # final HTTP response code sent to caller

    def to_dict(self) -> Dict[str, Any]:
        return {
            "request_id": self.request_id,
            "route": self.route,
            "method": self.method,
            "headers": self.headers,
            "payload": self.payload,
            "source_ip": self.source_ip,
            "timestamp": self.timestamp,
            "status_code": self.status_code,
        }


class RequestLog:
    def __init__(self, max_size: int = 500) -> None:
        self._max_size = max_size
        self._entries: List[RequestEntry] = []
        self._counter = 0

    def _next_id(self) -> int:
        self._counter += 1
        return self._counter

    def record(
        self,
        route: str,
        method: str,
        headers: Dict[str, str],
        payload: Any,
        source_ip: str,
        status_code: Optional[int] = None,
    ) -> RequestEntry:
        entry = RequestEntry(
            request_id=self._next_id(),
            route=route,
            method=method,
            headers=headers,
            payload=payload,
            source_ip=source_ip,
            status_code=status_code,
        )
        self._entries.append(entry)
        if len(self._entries) > self._max_size:
            self._entries.pop(0)
        return entry

    def all(self) -> List[RequestEntry]:
        return list(self._entries)

    def for_route(self, route: str) -> List[RequestEntry]:
        return [e for e in self._entries if e.route == route]

    def get(self, request_id: int) -> Optional[RequestEntry]:
        for entry in self._entries:
            if entry.request_id == request_id:
                return entry
        return None

    def clear(self) -> None:
        self._entries.clear()

    def size(self) -> int:
        return len(self._entries)
