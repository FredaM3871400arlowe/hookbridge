"""HTTP handler mixin that exposes per-route payload size limit configuration."""

import json
from http.server import BaseHTTPRequestHandler
from typing import List

from hookbridge.payload_size_limiter import (
    SizeLimitConfig,
    config_from_dict,
    _DEFAULT_MAX_BYTES,
)


def _route_size_info(route) -> dict:
    """Return a JSON-serialisable dict describing the size limit for a route."""
    raw = getattr(route, "size_limit", None)
    if raw is None:
        cfg = SizeLimitConfig()
    elif isinstance(raw, SizeLimitConfig):
        cfg = raw
    else:
        cfg = config_from_dict(raw)
    return {
        "route": route.path,
        "max_bytes": cfg.max_bytes,
        "default": raw is None,
    }


def add_size_limit_routes(handler_class: type) -> type:
    """Class decorator that injects GET /size-limits into a handler class."""
    original_do_get = getattr(handler_class, "do_GET", None)

    def do_GET(self):
        if self.path == "/size-limits":
            self._serve_size_limits()
        elif original_do_get:
            original_do_get(self)
        else:
            self.send_response(404)
            self.end_headers()

    handler_class.do_GET = do_GET
    handler_class._serve_size_limits = _serve_size_limits
    return handler_class


def _serve_size_limits(self):
    """Respond with JSON listing size limits for every configured route."""
    routes = getattr(self.server, "config", None)
    route_list = getattr(routes, "routes", []) if routes else []
    payload = json.dumps([_route_size_info(r) for r in route_list]).encode()
    self.send_response(200)
    self.send_header("Content-Type", "application/json")
    self.send_header("Content-Length", str(len(payload)))
    self.end_headers()
    self.wfile.write(payload)


class SizeLimitAwareHandler(BaseHTTPRequestHandler):
    """Standalone handler subclass with size-limit introspection endpoint."""

    def do_GET(self):
        if self.path == "/size-limits":
            _serve_size_limits(self)
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, fmt, *args):  # pragma: no cover
        pass
