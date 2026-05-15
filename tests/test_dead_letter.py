"""Tests for the dead-letter queue and its HTTP handler."""

import json
import time
import io
from unittest.mock import MagicMock

import pytest

from hookbridge.dead_letter import DeadLetterEntry, DeadLetterQueue
from hookbridge.dead_letter_handler import add_dead_letter_routes


# ---------------------------------------------------------------------------
# DeadLetterQueue unit tests
# ---------------------------------------------------------------------------

@pytest.fixture
def dlq():
    return DeadLetterQueue(max_size=5)


def _entry(route_id="r1", error="timeout", status=None, ts=None):
    return DeadLetterEntry(
        route_id=route_id,
        target_url="https://example.com/hook",
        payload={"event": "push"},
        error=error,
        status_code=status,
        failed_at=ts or time.time(),
    )


def test_push_and_size(dlq):
    dlq.push(_entry())
    assert dlq.size() == 1


def test_max_size_evicts_oldest(dlq):
    for i in range(6):
        dlq.push(_entry(route_id=f"r{i}"))
    assert dlq.size() == 5
    # oldest (r0) should have been evicted
    assert dlq.all()[0].route_id == "r1"


def test_for_route_filters(dlq):
    dlq.push(_entry(route_id="a"))
    dlq.push(_entry(route_id="b"))
    dlq.push(_entry(route_id="a"))
    assert len(dlq.for_route("a")) == 2
    assert len(dlq.for_route("b")) == 1


def test_remove_entry(dlq):
    e = _entry(ts=1234567890.0)
    dlq.push(e)
    assert dlq.remove("r1", 1234567890.0) is True
    assert dlq.size() == 0


def test_remove_nonexistent(dlq):
    assert dlq.remove("nope", 0.0) is False


def test_clear(dlq):
    dlq.push(_entry())
    dlq.push(_entry())
    dlq.clear()
    assert dlq.size() == 0


def test_to_json(dlq):
    dlq.push(_entry(route_id="x", status=503))
    data = json.loads(dlq.to_json())
    assert len(data) == 1
    assert data[0]["route_id"] == "x"
    assert data[0]["status_code"] == 503


# ---------------------------------------------------------------------------
# HTTP handler tests
# ---------------------------------------------------------------------------

def _make_handler(path, dlq):
    from http.server import BaseHTTPRequestHandler

    HandlerClass = add_dead_letter_routes(BaseHTTPRequestHandler, dlq)

    handler = HandlerClass.__new__(HandlerClass)
    handler.path = path
    handler.wfile = io.BytesIO()
    handler.send_response = MagicMock()
    handler.send_header = MagicMock()
    handler.end_headers = MagicMock()
    return handler


def test_get_dead_letters_empty():
    dlq = DeadLetterQueue()
    h = _make_handler("/dead-letters", dlq)
    h.do_GET()
    h.wfile.seek(0)
    data = json.loads(h.wfile.read())
    assert data["count"] == 0
    assert data["entries"] == []


def test_get_dead_letters_with_entries():
    dlq = DeadLetterQueue()
    dlq.push(_entry(route_id="webhook-1"))
    h = _make_handler("/dead-letters", dlq)
    h.do_GET()
    h.wfile.seek(0)
    data = json.loads(h.wfile.read())
    assert data["count"] == 1


def test_get_dead_letters_filtered_by_route():
    dlq = DeadLetterQueue()
    dlq.push(_entry(route_id="a"))
    dlq.push(_entry(route_id="b"))
    h = _make_handler("/dead-letters?route=a", dlq)
    h.do_GET()
    h.wfile.seek(0)
    data = json.loads(h.wfile.read())
    assert data["count"] == 1
    assert data["entries"][0]["route_id"] == "a"


def test_delete_clears_queue():
    dlq = DeadLetterQueue()
    dlq.push(_entry())
    h = _make_handler("/dead-letters", dlq)
    h.do_DELETE()
    assert dlq.size() == 0
    h.wfile.seek(0)
    data = json.loads(h.wfile.read())
    assert data["cleared"] is True
