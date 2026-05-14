import json
import pytest
from unittest.mock import MagicMock, patch
from io import BytesIO

from hookbridge.config import AppConfig, RouteConfig
from hookbridge.server import create_server, WebhookHandler
from hookbridge.dispatcher import DispatchResult


ROUTE = RouteConfig(
    path="/webhook",
    target_url="http://example.com/target",
    filters=[],
    transform=None,
    retry_count=0,
    timeout=5,
)

CONFIG = AppConfig(host="127.0.0.1", port=9000, routes=[ROUTE])


def make_handler(method: str, path: str, body: dict | None = None):
    """Build a WebhookHandler instance wired to a mock socket."""
    raw_body = json.dumps(body).encode() if body is not None else b""
    request = MagicMock()
    request.makefile = MagicMock(
        side_effect=lambda mode, *a, **kw: (
            BytesIO(
                f"{method} {path} HTTP/1.1\r\n"
                f"Content-Length: {len(raw_body)}\r\n"
                f"Content-Type: application/json\r\n\r\n".encode()
                + raw_body
            )
            if "r" in mode
            else BytesIO()
        )
    )
    WebhookHandler.config = CONFIG
    handler = WebhookHandler.__new__(WebhookHandler)
    handler.rfile = BytesIO(raw_body)
    handler.wfile = BytesIO()
    handler.headers = {"Content-Length": str(len(raw_body)), "Content-Type": "application/json"}
    handler.path = path
    handler.command = method
    handler.request_version = "HTTP/1.1"
    handler.server = MagicMock()
    handler.client_address = ("127.0.0.1", 12345)
    return handler


def test_create_server_sets_config():
    server = create_server(CONFIG)
    assert WebhookHandler.config is CONFIG
    server.server_close()


def test_post_unknown_path_returns_404():
    handler = make_handler("POST", "/unknown", {})
    responses = []
    handler.send_json = lambda status, body: responses.append((status, body))
    handler.do_POST()
    assert responses[0][0] == 404


def test_post_invalid_json_returns_400():
    handler = make_handler("POST", "/webhook")
    handler.rfile = BytesIO(b"{not valid json")
    handler.headers = {"Content-Length": "15"}
    responses = []
    handler.send_json = lambda status, body: responses.append((status, body))
    handler.do_POST()
    assert responses[0][0] == 400


def test_post_valid_payload_all_success():
    handler = make_handler("POST", "/webhook", {"event": "ping"})
    ok_result = DispatchResult(target_url="http://example.com/target", success=True, detail="200")
    responses = []
    handler.send_json = lambda status, body: responses.append((status, body))
    with patch("hookbridge.server.dispatch_all", return_value=[ok_result]):
        handler.do_POST()
    status, body = responses[0]
    assert status == 200
    assert body["dispatched"] == 1
    assert body["results"][0]["success"] is True


def test_post_partial_failure_returns_207():
    handler = make_handler("POST", "/webhook", {"event": "push"})
    results = [
        DispatchResult(target_url="http://a.com", success=True, detail="200"),
        DispatchResult(target_url="http://b.com", success=False, detail="timeout"),
    ]
    responses = []
    handler.send_json = lambda status, body: responses.append((status, body))
    with patch("hookbridge.server.dispatch_all", return_value=results):
        handler.do_POST()
    assert responses[0][0] == 207
