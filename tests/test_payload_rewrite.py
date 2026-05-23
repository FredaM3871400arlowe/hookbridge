"""Tests for hookbridge.payload_rewrite and hookbridge.payload_rewrite_handler."""

import io
import json
from unittest.mock import MagicMock

import pytest

from hookbridge.payload_rewrite import (
    PayloadRewriteConfig,
    apply_payload_rewrites,
    config_from_dict,
    get_route_rewrite_config,
)


# ---------------------------------------------------------------------------
# config_from_dict
# ---------------------------------------------------------------------------

def test_config_from_dict_defaults():
    cfg = config_from_dict({})
    assert cfg.rename == {}
    assert cfg.drop == []
    assert cfg.set_fields == {}


def test_config_from_dict_full():
    cfg = config_from_dict({"rename": {"old": "new"}, "drop": ["secret"], "set": {"source": "hookbridge"}})
    assert cfg.rename == {"old": "new"}
    assert cfg.drop == ["secret"]
    assert cfg.set_fields == {"source": "hookbridge"}


def test_get_route_rewrite_config_none_when_absent():
    route = MagicMock(spec=[])
    assert get_route_rewrite_config(route) is None


def test_get_route_rewrite_config_returns_config():
    route = MagicMock()
    route.payload_rewrite = {"drop": ["token"]}
    cfg = get_route_rewrite_config(route)
    assert isinstance(cfg, PayloadRewriteConfig)
    assert cfg.drop == ["token"]


# ---------------------------------------------------------------------------
# apply_payload_rewrites
# ---------------------------------------------------------------------------

def test_apply_drop_removes_key():
    cfg = PayloadRewriteConfig(drop=["secret"])
    result = apply_payload_rewrites({"event": "push", "secret": "abc"}, cfg)
    assert "secret" not in result
    assert result["event"] == "push"


def test_apply_rename_renames_key():
    cfg = PayloadRewriteConfig(rename={"ref": "branch"})
    result = apply_payload_rewrites({"ref": "main", "id": 1}, cfg)
    assert "branch" in result
    assert result["branch"] == "main"
    assert "ref" not in result


def test_apply_rename_missing_key_is_noop():
    cfg = PayloadRewriteConfig(rename={"nonexistent": "other"})
    payload = {"a": 1}
    result = apply_payload_rewrites(payload, cfg)
    assert result == {"a": 1}


def test_apply_set_injects_value():
    cfg = PayloadRewriteConfig(set_fields={"env": "prod"})
    result = apply_payload_rewrites({"event": "deploy"}, cfg)
    assert result["env"] == "prod"


def test_apply_set_overwrites_existing():
    cfg = PayloadRewriteConfig(set_fields={"status": "ok"})
    result = apply_payload_rewrites({"status": "pending"}, cfg)
    assert result["status"] == "ok"


def test_apply_order_drop_before_rename():
    # drop 'a', then rename 'b' -> 'a'; result should have 'a' from rename
    cfg = PayloadRewriteConfig(drop=["a"], rename={"b": "a"})
    result = apply_payload_rewrites({"a": "original", "b": "renamed"}, cfg)
    assert result["a"] == "renamed"


def test_apply_does_not_mutate_original():
    cfg = PayloadRewriteConfig(drop=["x"], rename={"y": "z"}, set_fields={"w": 1})
    original = {"x": 1, "y": 2}
    apply_payload_rewrites(original, cfg)
    assert original == {"x": 1, "y": 2}


# ---------------------------------------------------------------------------
# payload_rewrite_handler (integration-style)
# ---------------------------------------------------------------------------

def _make_handler(routes=None):
    from hookbridge.payload_rewrite_handler import RewriteAwareHandler

    server = MagicMock()
    cfg = MagicMock()
    cfg.routes = routes or []
    server.config = cfg

    buf = io.BytesIO()
    handler = RewriteAwareHandler.__new__(RewriteAwareHandler)
    handler.server = server
    handler.wfile = buf
    handler.rfile = io.BytesIO()
    handler.headers = {}

    responses = []
    handler.send_response = lambda code: responses.append(code)
    handler.send_header = lambda k, v: None
    handler.end_headers = lambda: None
    handler._responses = responses
    return handler, buf


def _make_route(path, rewrite_cfg=None):
    route = MagicMock()
    route.path = path
    route.payload_rewrite = rewrite_cfg
    return route


def test_get_all_rewrites_empty():
    handler, buf = _make_handler([])
    handler.path = "/rewrite"
    handler.do_GET()
    buf.seek(0)
    data = json.loads(buf.read())
    assert data == []


def test_get_all_rewrites_with_route():
    route = _make_route("/hook", {"drop": ["token"], "rename": {}, "set": {}})
    handler, buf = _make_handler([route])
    handler.path = "/rewrite"
    handler.do_GET()
    buf.seek(0)
    data = json.loads(buf.read())
    assert len(data) == 1
    assert data[0]["route"] == "/hook"
    assert data[0]["drop"] == ["token"]


def test_get_single_route_found():
    route = _make_route("/hook", {"set": {"env": "prod"}})
    handler, buf = _make_handler([route])
    handler.path = "/rewrite/hook"
    handler.do_GET()
    buf.seek(0)
    data = json.loads(buf.read())
    assert data["set"] == {"env": "prod"}


def test_get_single_route_not_found():
    handler, buf = _make_handler([])
    handler.path = "/rewrite/missing"
    handler.do_GET()
    assert handler._responses[-1] == 404
