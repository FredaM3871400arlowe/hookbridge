"""HTTP handler routes for managing webhook secret rotation.

GET  /rotation/<route_id>          — list active secrets (masked)
POST /rotation/<route_id>          — add a new secret  {"secret": "...", "ttl": 300}
DELETE /rotation/<route_id>        — drop all secrets for a route
"""

from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler
from typing import Type

from hookbridge.webhook_signature_rotator import get_rotator, reset_rotators


def add_rotation_routes(handler_class: Type[BaseHTTPRequestHandler]) -> Type[BaseHTTPRequestHandler]:
    """Mixin rotation route handling into *handler_class*."""

    class RotationAwareHandler(handler_class):  # type: ignore[valid-type]
        def do_GET(self):
            if self.path.startswith("/rotation/"):
                self._serve_rotation()
            else:
                super().do_GET()

        def do_POST(self):
            if self.path.startswith("/rotation/"):
                route_id = self.path[len("/rotation/"):].strip("/")
                length = int(self.headers.get("Content-Length", 0))
                body = self.rfile.read(length) if length else b"{}"
                try:
                    data = json.loads(body)
                except json.JSONDecodeError:
                    self.send_response(400)
                    self.end_headers()
                    return
                secret = data.get("secret", "")
                if not secret:
                    self.send_response(400)
                    self.end_headers()
                    return
                ttl = data.get("ttl")  # optional float seconds
                get_rotator(route_id).add_secret(secret, ttl_seconds=ttl)
                self.send_response(204)
                self.end_headers()
            else:
                super().do_POST()

        def do_DELETE(self):
            if self.path.startswith("/rotation/"):
                route_id = self.path[len("/rotation/"):].strip("/")
                reset_rotators.__module__  # noqa — ensure import
                from hookbridge.webhook_signature_rotator import _rotators
                _rotators.pop(route_id, None)
                self.send_response(204)
                self.end_headers()
            else:
                super().do_DELETE()

        def _serve_rotation(self):
            route_id = self.path[len("/rotation/"):].strip("/")
            rotator = get_rotator(route_id)
            secrets = rotator.all_active_secrets()
            masked = [{"hint": s[:4] + "****", "index": i} for i, s in enumerate(secrets)]
            payload = json.dumps({"route": route_id, "active_secrets": masked}).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

    RotationAwareHandler.__name__ = handler_class.__name__
    return RotationAwareHandler
