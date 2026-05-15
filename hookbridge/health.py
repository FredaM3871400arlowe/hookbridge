"""Health check endpoint for hookbridge server."""

import json
import time
from http.server import BaseHTTPRequestHandler
from typing import Optional

_start_time: float = time.time()


def get_uptime_seconds() -> float:
    """Return seconds since the server module was first imported."""
    return time.time() - _start_time


def build_health_payload(
    metrics_collector=None,
    dlq=None,
) -> dict:
    """Build the health status dictionary.

    Args:
        metrics_collector: Optional MetricsCollector instance.
        dlq: Optional DeadLetterQueue instance.

    Returns:
        A dict suitable for JSON serialisation.
    """
    payload: dict = {
        "status": "ok",
        "uptime_seconds": round(get_uptime_seconds(), 3),
    }

    if metrics_collector is not None:
        try:
            summary = metrics_collector.summary()
            payload["routes_tracked"] = len(summary)
            total_ok = sum(r.get("success", 0) for r in summary.values())
            total_fail = sum(r.get("failure", 0) for r in summary.values())
            payload["total_success"] = total_ok
            payload["total_failure"] = total_fail
        except Exception:  # pragma: no cover
            payload["metrics"] = "unavailable"

    if dlq is not None:
        try:
            payload["dead_letter_queue_size"] = dlq.size()
        except Exception:  # pragma: no cover
            payload["dead_letter_queue_size"] = "unavailable"

    return payload


def add_health_route(
    handler_class,
    metrics_collector=None,
    dlq=None,
):
    """Mixin a /health GET handler into *handler_class* in-place.

    Patches the class so that GET /health returns a JSON health payload.
    """
    _mc = metrics_collector
    _dlq = dlq

    original_do_get = getattr(handler_class, "do_GET", None)

    def do_GET(self):
        if self.path == "/health":
            _serve_health(self, _mc, _dlq)
        elif original_do_get is not None:
            original_do_get(self)
        else:
            self.send_response(404)
            self.end_headers()

    handler_class.do_GET = do_GET
    return handler_class


def _serve_health(handler, metrics_collector, dlq):
    payload = build_health_payload(metrics_collector, dlq)
    body = json.dumps(payload).encode()
    handler.send_response(200)
    handler.send_header("Content-Type", "application/json")
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)
