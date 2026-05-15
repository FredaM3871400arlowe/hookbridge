"""Tests for hookbridge/event_log_handler.py"""

import json
import io
from http.server import BaseHTTPRequestHandler
from unittest.mock import MagicMock

import pytest

from hookbridge.event_log import EventLog
from hookbridge.event_log_handler import add_event_log_routes


def _make_handler(path, event_log, method="GET"):
    HandlerClass = add_event_log_routes(BaseHTTPRequestHandler)
    HandlerClass.event_log = event_log

    request = MagicMock()
    buf = io.BytesIO()

    def makefile(mode, *a, **kw):
        if "w" in mode:
            return io.TextIOWrapper(buf, write_through=True)
        return io.BytesIO(b"")

    request.makefile = makefile

    handler = HandlerClass.__new__(HandlerClass)
    handler.path = path
    handler.request = request
    handler.client_address = ("127.0.0.1", 9999)
    handler.server = MagicMock()
    handler.wfile = buf
    handler.rfile = io.BytesIO(b"")
    handler.headers = {}
    handler.command = method

    responses = []
    headers_sent = []

    def send_response(code):
        responses.append(code)

    def send_header(k, v):
        headers_sent.append((k, v))

    def end_headers():
        pass

    handler.send_response = send_response
    handler.send_header = send_header
    handler.end_headers = end_headers
    handler._responses = responses
    handler._buf = buf
    return handler


def _read_json(handler):
    handler._buf.seek(0)
    return json.loads(handler._buf.read())


def test_get_events_empty():
    log = EventLog()
    h = _make_handler("/events", log)
    h.do_GET()
    assert h._responses == [200]
    assert _read_json(h) == []


def test_get_events_returns_entries():
    log = EventLog()
    log.record("gh", "success", "http://target.com", http_status=200)
    h = _make_handler("/events", log)
    h.do_GET()
    data = _read_json(h)
    assert len(data) == 1
    assert data[0]["route"] == "gh"


def test_get_events_filter_by_route():
    log = EventLog()
    log.record("alpha", "success", "http://a.com")
    log.record("beta", "success", "http://b.com")
    h = _make_handler("/events?route=alpha", log)
    h.do_GET()
    data = _read_json(h)
    assert len(data) == 1
    assert data[0]["route"] == "alpha"


def test_get_event_by_id():
    log = EventLog()
    entry = log.record("r", "success", "http://x.com")
    h = _make_handler(f"/events/{entry.event_id}", log)
    h.do_GET()
    assert h._responses == [200]
    data = _read_json(h)
    assert data["event_id"] == entry.event_id


def test_get_event_by_id_not_found():
    log = EventLog()
    h = _make_handler("/events/9999", log)
    h.do_GET()
    assert h._responses == [404]


def test_delete_clears_log():
    log = EventLog()
    log.record("r", "success", "http://a.com")
    h = _make_handler("/events", log, method="DELETE")
    h.do_DELETE()
    assert h._responses == [200]
    assert log.size() == 0
