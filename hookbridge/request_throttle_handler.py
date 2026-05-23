"""HTTP handler routes for inspecting per-route throttle state."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from hookbridge.request_throttle import _states, _global_lock

if TYPE_CHECKING:
    from hookbridge.server import WebhookHandler


def add_throttle_routes(handler_class: type) -> type:
    """Mixin that adds GET /throttle to a handler class."""

    class ThrottleAwareHandler(handler_class):  # type: ignore[valid-type]
        def do_GET(self) -> None:
            if self.path == "/throttle":
                self._serve_throttle_all()
            elif self.path.startswith("/throttle/"):
                route_id = self.path[len("/throttle/"):]
                self._serve_throttle_route(route_id)
            else:
                super().do_GET()

        def _serve_throttle_all(self) -> None:
            with _global_lock:
                data = {rid: state.to_dict() for rid, state in _states.items()}
            body = json.dumps(data).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _serve_throttle_route(self, route_id: str) -> None:
            with _global_lock:
                state = _states.get(route_id)
            if state is None:
                body = json.dumps({"error": "route not found"}).encode()
                self.send_response(404)
            else:
                body = json.dumps(state.to_dict()).encode()
                self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, fmt: str, *args: object) -> None:  # pragma: no cover
            pass

    ThrottleAwareHandler.__name__ = "ThrottleAwareHandler"
    return ThrottleAwareHandler
