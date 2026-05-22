"""Tests for hookbridge.circuit_breaker_handler HTTP endpoints."""

from __future__ import annotations

import io
import json
from http.server import BaseHTTPRequestHandler
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from hookbridge.circuit_breaker import CircuitBreaker, CircuitBreakerConfig
from hookbridge.circuit_breaker_handler import add_circuit_breaker_routes


def _make_handler(path: str, method: str = "GET") -> BaseHTTPRequestHandler:
    @add_circuit_breaker_routes
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, fmt, *args):  # noqa: D401
            pass

    cfg = CircuitBreakerConfig(failure_threshold=2, recovery_timeout=30.0, success_threshold=1)
    cb = CircuitBreaker(config=cfg)

    server = SimpleNamespace(circuit_breaker=cb)
    rfile = io.BytesIO(b"")
    wfile = io.BytesIO()

    handler = Handler.__new__(Handler)
    handler.path = path
    handler.command = method
    handler.server = server
    handler.rfile = rfile
    handler.wfile = wfile
    handler.headers = {}
    handler.send_response = MagicMock()
    handler.send_header = MagicMock()
    handler.end_headers = MagicMock()
    return handler


def test_get_all_circuit_breakers_empty() -> None:
    h = _make_handler("/__hookbridge/circuit-breakers")
    h.do_GET()
    h.send_response.assert_called_once_with(200)
    written = h.wfile.getvalue()
    data = json.loads(written)
    assert data == {}


def test_get_all_circuit_breakers_with_data() -> None:
    h = _make_handler("/__hookbridge/circuit-breakers")
    h.server.circuit_breaker.record_failure("route-a")
    h.do_GET()
    written = h.wfile.getvalue()
    data = json.loads(written)
    assert "route-a" in data
    assert data["route-a"]["failure_count"] == 1


def test_delete_resets_route() -> None:
    h = _make_handler("/__hookbridge/circuit-breakers/route-a", "DELETE")
    cb: CircuitBreaker = h.server.circuit_breaker
    cb.record_failure("route-a")
    cb.record_failure("route-a")  # opens the circuit
    h.do_DELETE()
    h.send_response.assert_called_once_with(204)
    from hookbridge.circuit_breaker import CircuitState
    assert cb.get_state("route-a").state == CircuitState.CLOSED


def test_get_unknown_path_returns_404() -> None:
    h = _make_handler("/unknown")
    h.do_GET()
    h.send_response.assert_called_once_with(404)


def test_delete_missing_route_name_returns_404() -> None:
    h = _make_handler("/__hookbridge/circuit-breakers/", "DELETE")
    h.do_DELETE()
    h.send_response.assert_called_once_with(404)
