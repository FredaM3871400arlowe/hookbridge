"""HTTP handler extension that exposes a /metrics endpoint."""

import json
from http.server import BaseHTTPRequestHandler
from typing import Type

from hookbridge.metrics import get_collector

METRICS_PATH = "/_/metrics"


def add_metrics_route(
    base_class: Type[BaseHTTPRequestHandler],
) -> Type[BaseHTTPRequestHandler]:
    """Mixin factory: wraps an existing handler class to serve /metrics."""

    class MetricsAwareHandler(base_class):  # type: ignore[valid-type]
        def do_GET(self) -> None:  # noqa: N802
            if self.path == METRICS_PATH:
                self._serve_metrics()
            else:
                self.send_response(404)
                self.end_headers()

        def _serve_metrics(self) -> None:
            collector = get_collector()
            data = collector.snapshot()
            body = json.dumps({"routes": data}, indent=2).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, fmt: str, *args: object) -> None:  # type: ignore[override]
            pass  # suppress default stderr logging

    MetricsAwareHandler.__name__ = f"MetricsAware{base_class.__name__}"
    return MetricsAwareHandler
