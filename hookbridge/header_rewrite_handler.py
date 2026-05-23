"""HTTP handler routes for inspecting per-route header rewrite configuration."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from hookbridge.header_rewrite import get_route_rewrite_config

if TYPE_CHECKING:
    from hookbridge.server import WebhookHandler


def add_header_rewrite_routes(handler_class: type) -> type:
    """Mixin *add_header_rewrite_routes* into *handler_class* and return it."""

    original_get = getattr(handler_class, "do_GET", None)

    def do_GET(self: "WebhookHandler") -> None:  # type: ignore[override]
        if self.path == "/header-rewrites":
            self._serve_header_rewrites()
        elif original_get:
            original_get(self)
        else:
            self.send_response(404)
            self.end_headers()

    handler_class.do_GET = do_GET  # type: ignore[attr-defined]
    return handler_class


class HeaderRewriteAwareHandler:
    """Mixin that adds ``/header-rewrites`` introspection to a handler."""

    def do_GET(self) -> None:  # type: ignore[override]
        if self.path == "/header-rewrites":  # type: ignore[attr-defined]
            self._serve_header_rewrites()
        else:
            super().do_GET()  # type: ignore[misc]

    def _serve_header_rewrites(self) -> None:
        config = getattr(self, "server", None)
        app_config = getattr(config, "app_config", None)
        routes = getattr(app_config, "routes", []) if app_config else []

        payload: dict = {}
        for route in routes:
            rc = get_route_rewrite_config(route)
            if rc is not None:
                payload[route.path] = {
                    "add": rc.add,
                    "set": rc.set,
                    "remove": rc.remove,
                }

        body = json.dumps(payload).encode()
        self.send_response(200)  # type: ignore[attr-defined]
        self.send_header("Content-Type", "application/json")  # type: ignore[attr-defined]
        self.send_header("Content-Length", str(len(body)))  # type: ignore[attr-defined]
        self.end_headers()  # type: ignore[attr-defined]
        self.wfile.write(body)  # type: ignore[attr-defined]

    def log_message(self, *args, **kwargs) -> None:  # noqa: D401
        pass
