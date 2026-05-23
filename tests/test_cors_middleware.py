"""Tests for CORS middleware (apply_cors_to_handler, flush_cors_headers)."""

import pytest
from unittest.mock import MagicMock, call
from hookbridge.cors import CORSConfig
from hookbridge.cors_middleware import apply_cors_to_handler, flush_cors_headers, _get_origin


def _make_handler(method="POST", origin=None):
    handler = MagicMock()
    handler.command = method
    raw_headers = {"Content-Type": "application/json"}
    if origin:
        raw_headers["Origin"] = origin
    handler.headers = raw_headers
    handler._pending_cors_headers = {}
    return handler


def test_apply_cors_returns_false_for_normal_post():
    handler = _make_handler("POST", origin="https://example.com")
    cfg = CORSConfig()
    result = apply_cors_to_handler(handler, cfg)
    assert result is False


def test_apply_cors_returns_true_for_preflight():
    handler = _make_handler("OPTIONS", origin="https://example.com")
    cfg = CORSConfig()
    result = apply_cors_to_handler(handler, cfg)
    assert result is True
    handler.send_response.assert_called_once_with(204)
    handler.end_headers.assert_called_once()


def test_apply_cors_none_config_is_noop():
    handler = _make_handler("OPTIONS", origin="https://example.com")
    result = apply_cors_to_handler(handler, None)
    assert result is False
    handler.send_response.assert_not_called()


def test_pending_cors_headers_set_for_non_preflight():
    handler = _make_handler("POST", origin="https://example.com")
    cfg = CORSConfig(allowed_origins=["https://example.com"])
    apply_cors_to_handler(handler, cfg)
    assert "Access-Control-Allow-Origin" in handler._pending_cors_headers
    assert handler._pending_cors_headers["Access-Control-Allow-Origin"] == "https://example.com"


def test_flush_cors_headers_calls_send_header():
    handler = _make_handler()
    handler._pending_cors_headers = {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Max-Age": "600",
    }
    flush_cors_headers(handler)
    calls = {c.args[0] for c in handler.send_header.call_args_list}
    assert "Access-Control-Allow-Origin" in calls
    assert "Access-Control-Max-Age" in calls
    assert handler._pending_cors_headers == {}


def test_flush_cors_headers_empty_is_safe():
    handler = _make_handler()
    handler._pending_cors_headers = {}
    flush_cors_headers(handler)  # should not raise
    handler.send_header.assert_not_called()


def test_get_origin_case_insensitive():
    handler = _make_handler()
    handler.headers = {"ORIGIN": "https://caps.example.com"}
    assert _get_origin(handler) == "https://caps.example.com"


def test_get_origin_missing_returns_none():
    handler = _make_handler()
    handler.headers = {"Content-Type": "application/json"}
    assert _get_origin(handler) is None
