"""HTTP handler mixin that exposes GET /rewrite to inspect per-route payload rewrite rules."""

from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler

from hookbridge.payload_rewrite import config_from_dict


def _route_rewrite_info(route) -> dict:
    raw = getattr(route, "payload_rewrite", None) or {}
    cfg = config_from_dict(raw)
    return {
        "route": route.path,
        "rename": cfg.rename,
        "drop": cfg.drop,
        "set": cfg.set_fields,
    }


def add_rewrite_routes(handler_class: type) -> type:
    """Class decorator – mixes payload-rewrite inspection into a handler."""
    original_do_get = getattr(handler_class, "do_GET", None)

    def do_GET(self):
        if self.path == "/rewrite":
            self._serve_rewrite_all()
        elif self.path.startswith("/rewrite/"):
            route_path = "/" + self.path[len("/rewrite/"):]
            self._serve_rewrite_route(route_path)
        elif original_do_get:
            original_do_get(self)
        else:
            self.send_response(404)
            self.end_headers()

    def _serve_rewrite_all(self):
        routes = getattr(self.server, "config", None)
        entries = []
        if routes:
            for route in routes.routes:
                entries.append(_route_rewrite_info(route))
        body = json.dumps(entries).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _serve_rewrite_route(self, route_path: str):
        routes = getattr(self.server, "config", None)
        if routes:
            for route in routes.routes:
                if route.path == route_path:
                    body = json.dumps(_route_rewrite_info(route)).encode()
                    self.send_response(200)
                    self.send_header("Content-Type", "application/json")
                    self.send_header("Content-Length", str(len(body)))
                    self.end_headers()
                    self.wfile.write(body)
                    return
        self.send_response(404)
        self.end_headers()

    handler_class.do_GET = do_GET
    handler_class._serve_rewrite_all = _serve_rewrite_all
    handler_class._serve_rewrite_route = _serve_rewrite_route
    return handler_class


@add_rewrite_routes
class RewriteAwareHandler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):  # silence default stderr logging
        pass
