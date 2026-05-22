"""HTTP handler mixin that exposes a GET /schemas endpoint."""

import json
from http.server import BaseHTTPRequestHandler
from typing import Any


def add_schema_routes(handler_class: type) -> type:
    """Extend *handler_class* with schema introspection routes."""

    original_do_get = getattr(handler_class, "do_GET", None)

    def do_GET(self: Any) -> None:  # noqa: N802
        if self.path == "/schemas":
            self._serve_schemas()
        elif original_do_get:
            original_do_get(self)
        else:
            self.send_response(404)
            self.end_headers()

    handler_class.do_GET = do_GET
    handler_class._serve_schemas = _serve_schemas
    return handler_class


def _serve_schemas(self: Any) -> None:
    """Return all route schemas as a JSON object keyed by route path."""
    config = getattr(self.server, "config", None)
    routes = getattr(config, "routes", []) if config else []
    schemas = {
        route.path: route.payload_schema
        for route in routes
        if getattr(route, "payload_schema", None) is not None
    }
    body = json.dumps(schemas).encode("utf-8")
    self.send_response(200)
    self.send_header("Content-Type", "application/json")
    self.send_header("Content-Length", str(len(body)))
    self.end_headers()
    self.wfile.write(body)


class SchemaAwareHandler(BaseHTTPRequestHandler):
    """Standalone handler that includes the /schemas endpoint."""

    def do_GET(self) -> None:  # noqa: N802
        if self.path == "/schemas":
            _serve_schemas(self)
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, fmt: str, *args: Any) -> None:  # pragma: no cover
        pass
