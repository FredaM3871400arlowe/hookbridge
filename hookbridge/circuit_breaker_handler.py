"""HTTP handler mixin that exposes circuit-breaker state via GET/DELETE."""

from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from hookbridge.circuit_breaker import CircuitBreaker

_CB_PREFIX = "/__hookbridge/circuit-breakers"


def add_circuit_breaker_routes(handler_class: type) -> type:
    """Class decorator that injects circuit-breaker endpoints into a handler."""
    original_get = getattr(handler_class, "do_GET", None)
    original_delete = getattr(handler_class, "do_DELETE", None)

    def do_GET(self: BaseHTTPRequestHandler) -> None:
        if self.path == _CB_PREFIX or self.path == _CB_PREFIX + "/":
            return self._serve_circuit_breakers()
        if original_get:
            return original_get(self)
        self.send_response(404)
        self.end_headers()

    def do_DELETE(self: BaseHTTPRequestHandler) -> None:
        if self.path.startswith(_CB_PREFIX + "/"):
            route = self.path[len(_CB_PREFIX) + 1:]
            if route:
                cb: CircuitBreaker = self.server.circuit_breaker
                cb.reset(route)
                self.send_response(204)
                self.end_headers()
                return
        if original_delete:
            return original_delete(self)
        self.send_response(404)
        self.end_headers()

    def _serve_circuit_breakers(self: BaseHTTPRequestHandler) -> None:
        cb: CircuitBreaker = self.server.circuit_breaker
        body = json.dumps(cb.all_states()).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    handler_class.do_GET = do_GET
    handler_class.do_DELETE = do_DELETE
    handler_class._serve_circuit_breakers = _serve_circuit_breakers
    return handler_class


class CircuitBreakerAwareHandler(BaseHTTPRequestHandler):
    """Standalone handler base that includes circuit-breaker endpoints."""

    def log_message(self, fmt: str, *args: object) -> None:  # silence logs in tests
        pass
