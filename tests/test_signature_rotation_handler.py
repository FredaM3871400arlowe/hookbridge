"""Tests for hookbridge.signature_rotation_handler."""

import io
import json
import pytest

from http.server import BaseHTTPRequestHandler
from hookbridge.signature_rotation_handler import add_rotation_routes
from hookbridge.webhook_signature_rotator import reset_rotators, get_rotator


@pytest.fixture(autouse=True)
def clean():
    reset_rotators()
    yield
    reset_rotators()


def _make_handler(path: str, method: str = "GET", body: bytes = b""):
    class _Resp:
        def __init__(self):
            self.status = None
            self.headers = {}
            self.body = b""

    resp = _Resp()
    buf = io.BytesIO()

    Base = add_rotation_routes(BaseHTTPRequestHandler)

    class Handler(Base):
        def __init__(self):
            self.path = path
            self.headers = {"Content-Length": str(len(body))}
            self.rfile = io.BytesIO(body)
            self.wfile = buf
            self._resp = resp

        def send_response(self, code, *_):
            resp.status = code

        def send_header(self, k, v):
            resp.headers[k] = v

        def end_headers(self):
            pass

        def log_message(self, *_):
            pass

    h = Handler()
    getattr(h, f"do_{method}")()
    resp.body = buf.getvalue()
    return resp


def test_get_empty_rotation():
    resp = _make_handler("/rotation/my-route")
    assert resp.status == 200
    data = json.loads(resp.body)
    assert data["route"] == "my-route"
    assert data["active_secrets"] == []


def test_post_adds_secret():
    body = json.dumps({"secret": "supersecret"}).encode()
    resp = _make_handler("/rotation/route-1", method="POST", body=body)
    assert resp.status == 204
    assert get_rotator("route-1").primary_secret() == "supersecret"


def test_post_missing_secret_returns_400():
    body = json.dumps({"ttl": 60}).encode()
    resp = _make_handler("/rotation/route-1", method="POST", body=body)
    assert resp.status == 400


def test_post_invalid_json_returns_400():
    resp = _make_handler("/rotation/route-1", method="POST", body=b"not-json")
    assert resp.status == 400


def test_get_shows_masked_secrets():
    get_rotator("route-2").add_secret("abcd1234")
    resp = _make_handler("/rotation/route-2")
    data = json.loads(resp.body)
    hints = [s["hint"] for s in data["active_secrets"]]
    assert hints[0].startswith("abcd")
    assert "****" in hints[0]


def test_delete_removes_rotator():
    get_rotator("route-3").add_secret("todelete")
    resp = _make_handler("/rotation/route-3", method="DELETE")
    assert resp.status == 204
    # After deletion a fresh empty rotator is created on next access
    assert get_rotator("route-3").primary_secret() is None
