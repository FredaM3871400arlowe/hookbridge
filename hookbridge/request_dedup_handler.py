"""HTTP handler mixin that exposes deduplication state via GET /dedup."""

from __future__ import annotations

import json
from typing import Any

from hookbridge.request_dedup import _dedup_registry


def add_dedup_routes(handler_class: type) -> type:
    """Class decorator: bolt GET /dedup onto an existing handler class."""
    original_get = getattr(handler_class, "do_GET", None)

    def do_GET(self: Any) -> None:  # noqa: N802
        if self.path == "/dedup" or self.path.startswith("/dedup?"):
            self._serve_dedup_all()
        elif self.path.startswith("/dedup/"):
            route_id = self.path[len("/dedup/"):].split("?")[0]
            self._serve_dedup_route(route_id)
        elif original_get:
            original_get(self)
        else:
            self.send_response(404)
            self.end_headers()

    def do_DELETE(self: Any) -> None:  # noqa: N802
        if self.path.startswith("/dedup/"):
            route_id = self.path[len("/dedup/"):].split("?")[0]
            self._clear_dedup_route(route_id)
        else:
            self.send_response(404)
            self.end_headers()

    def _serve_dedup_all(self: Any) -> None:
        payload = {
            route_id: {"tracked_ids": dedup.size()}
            for route_id, dedup in _dedup_registry.items()
        }
        body = json.dumps(payload).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _serve_dedup_route(self: Any, route_id: str) -> None:
        dedup = _dedup_registry.get(route_id)
        if dedup is None:
            body = json.dumps({"error": "not_found", "route": route_id}).encode()
            self.send_response(404)
        else:
            body = json.dumps({"route": route_id, "tracked_ids": dedup.size()}).encode()
            self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _clear_dedup_route(self: Any, route_id: str) -> None:
        if route_id in _dedup_registry:
            del _dedup_registry[route_id]
            body = json.dumps({"cleared": route_id}).encode()
            self.send_response(200)
        else:
            body = json.dumps({"error": "not_found", "route": route_id}).encode()
            self.send_response(404)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    handler_class.do_GET = do_GET
    handler_class.do_DELETE = do_DELETE
    handler_class._serve_dedup_all = _serve_dedup_all
    handler_class._serve_dedup_route = _serve_dedup_route
    handler_class._clear_dedup_route = _clear_dedup_route
    return handler_class


@add_dedup_routes
class DedupAwareHandler:
    """Standalone handler base that includes /dedup routes."""

    def log_message(self, *args: Any) -> None:  # pragma: no cover
        pass
