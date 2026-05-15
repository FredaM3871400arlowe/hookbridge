"""HTTP handler that exposes the dead-letter queue via GET/DELETE endpoints."""

import json
from http.server import BaseHTTPRequestHandler
from hookbridge.dead_letter import DeadLetterQueue


def add_dead_letter_routes(handler_class: type, dlq: DeadLetterQueue) -> type:
    """Mixin dead-letter routes into an existing handler class."""

    class DeadLetterAwareHandler(handler_class):
        _dlq: DeadLetterQueue = dlq

        def do_GET(self):
            if self.path == "/dead-letters":
                self._serve_dead_letters()
            else:
                super().do_GET()

        def do_DELETE(self):
            if self.path == "/dead-letters":
                self._dlq.clear()
                self._send_json(200, {"cleared": True})
            else:
                self._send_json(404, {"error": "not found"})

        def _serve_dead_letters(self):
            route_id = None
            if "?" in self.path:
                qs = self.path.split("?", 1)[1]
                for part in qs.split("&"):
                    if part.startswith("route="):
                        route_id = part[len("route="):]

            entries = (
                self._dlq.for_route(route_id)
                if route_id
                else self._dlq.all()
            )
            body = json.dumps(
                {"count": len(entries), "entries": [e.to_dict() for e in entries]},
                indent=2,
            ).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _send_json(self, code: int, data: dict):
            body = json.dumps(data).encode()
            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, fmt, *args):  # silence test output
            pass

    return DeadLetterAwareHandler
