"""Tests for hookbridge/health.py"""

import json
import time
from io import BytesIO
from unittest.mock import MagicMock

import pytest

import hookbridge.health as health_mod
from hookbridge.health import (
    build_health_payload,
    get_uptime_seconds,
    add_health_route,
)


# ---------------------------------------------------------------------------
# get_uptime_seconds
# ---------------------------------------------------------------------------

def test_uptime_is_positive():
    assert get_uptime_seconds() >= 0


def test_uptime_increases():
    t1 = get_uptime_seconds()
    time.sleep(0.05)
    t2 = get_uptime_seconds()
    assert t2 > t1


# ---------------------------------------------------------------------------
# build_health_payload
# ---------------------------------------------------------------------------

def test_build_health_payload_minimal():
    payload = build_health_payload()
    assert payload["status"] == "ok"
    assert "uptime_seconds" in payload
    assert isinstance(payload["uptime_seconds"], float)


def test_build_health_payload_with_metrics():
    mc = MagicMock()
    mc.summary.return_value = {
        "route-a": {"success": 10, "failure": 2},
        "route-b": {"success": 5, "failure": 0},
    }
    payload = build_health_payload(metrics_collector=mc)
    assert payload["routes_tracked"] == 2
    assert payload["total_success"] == 15
    assert payload["total_failure"] == 2


def test_build_health_payload_with_dlq():
    dlq = MagicMock()
    dlq.size.return_value = 7
    payload = build_health_payload(dlq=dlq)
    assert payload["dead_letter_queue_size"] == 7


def test_build_health_payload_with_both():
    mc = MagicMock()
    mc.summary.return_value = {"r": {"success": 1, "failure": 0}}
    dlq = MagicMock()
    dlq.size.return_value = 3
    payload = build_health_payload(metrics_collector=mc, dlq=dlq)
    assert payload["status"] == "ok"
    assert payload["total_success"] == 1
    assert payload["dead_letter_queue_size"] == 3


# ---------------------------------------------------------------------------
# add_health_route / _serve_health
# ---------------------------------------------------------------------------

def _make_handler(path="/health"):
    """Return a minimal fake handler instance."""
    buf = BytesIO()

    class FakeHandler:
        wfile = buf
        _headers = {}
        _status = None

        def send_response(self, code):
            self._status = code

        def send_header(self, key, value):
            self._headers[key] = value

        def end_headers(self):
            pass

    handler = FakeHandler()
    handler.path = path
    return handler


def test_health_route_returns_200():
    handler = _make_handler("/health")
    add_health_route(handler.__class__)
    handler.do_GET()
    assert handler._status == 200


def test_health_route_returns_json():
    handler = _make_handler("/health")
    add_health_route(handler.__class__)
    handler.do_GET()
    handler.wfile.seek(0)
    data = json.loads(handler.wfile.read())
    assert data["status"] == "ok"


def test_health_route_unknown_path_returns_404():
    handler = _make_handler("/unknown")
    add_health_route(handler.__class__)
    handler.do_GET()
    assert handler._status == 404
