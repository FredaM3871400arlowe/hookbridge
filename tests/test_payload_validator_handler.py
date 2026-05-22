"""Tests for hookbridge.payload_validator_handler."""

import io
import json
from http.server import BaseHTTPRequestHandler
from unittest.mock import MagicMock

import pytest

from hookbridge.payload_validator_handler import add_schema_routes, SchemaAwareHandler


SCHEMA = {"type": "object", "properties": {"id": {"type": "integer"}}}


def _make_handler(path: str, routes=None):
    """Build a SchemaAwareHandler-like instance wired to a fake server."""
    server = MagicMock()
    cfg = MagicMock()
    cfg.routes = routes or []
    server.config = cfg

    buf = io.BytesIO()
    handler = SchemaAwareHandler.__new__(SchemaAwareHandler)
    handler.server = server
    handler.path = path
    handler.wfile = buf
    handler.rfile = io.BytesIO()
    handler.headers = {}

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
    handler._headers = headers_sent
    return handler


def _make_route(path, schema=None):
    r = MagicMock()
    r.path = path
    r.payload_schema = schema
    return r


def test_serve_schemas_empty():
    h = _make_handler("/schemas")
    h.do_GET()
    assert h._responses == [200]
    h.wfile.seek(0)
    data = json.loads(h.wfile.read())
    assert data == {}


def test_serve_schemas_with_routes():
    routes = [
        _make_route("/hook", SCHEMA),
        _make_route("/other", None),
    ]
    h = _make_handler("/schemas", routes=routes)
    h.do_GET()
    assert h._responses == [200]
    h.wfile.seek(0)
    data = json.loads(h.wfile.read())
    assert "/hook" in data
    assert "/other" not in data
    assert data["/hook"] == SCHEMA


def test_unknown_path_returns_404():
    h = _make_handler("/unknown")
    h.do_GET()
    assert h._responses == [404]


def test_add_schema_routes_extends_class():
    class DummyHandler(BaseHTTPRequestHandler):
        def log_message(self, fmt, *args):
            pass

    Extended = add_schema_routes(DummyHandler)
    assert hasattr(Extended, "do_GET")
    assert hasattr(Extended, "_serve_schemas")
