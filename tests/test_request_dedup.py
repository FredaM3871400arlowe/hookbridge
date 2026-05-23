"""Tests for hookbridge.request_dedup and hookbridge.request_dedup_handler."""

from __future__ import annotations

import json
import time
import types
from io import BytesIO
from unittest.mock import MagicMock, patch

import pytest

from hookbridge.request_dedup import (
    DedupConfig,
    RequestDeduplicator,
    build_dedup_response,
    check_dedup_for_route,
    config_from_dict,
    get_deduplicator,
    _dedup_registry,
)
from hookbridge.request_dedup_handler import add_dedup_routes


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def clear_registry():
    _dedup_registry.clear()
    yield
    _dedup_registry.clear()


# ---------------------------------------------------------------------------
# DedupConfig
# ---------------------------------------------------------------------------

def test_default_config_values():
    cfg = DedupConfig()
    assert cfg.window_seconds == 300
    assert cfg.max_entries == 10_000


def test_window_below_minimum_raises():
    with pytest.raises(ValueError, match="window_seconds"):
        DedupConfig(window_seconds=0)


def test_window_above_maximum_raises():
    with pytest.raises(ValueError, match="window_seconds"):
        DedupConfig(window_seconds=86_401)


def test_max_entries_zero_raises():
    with pytest.raises(ValueError, match="max_entries"):
        DedupConfig(max_entries=0)


def test_config_from_dict_custom():
    cfg = config_from_dict({"window_seconds": 60, "max_entries": 500})
    assert cfg.window_seconds == 60
    assert cfg.max_entries == 500


def test_config_from_dict_defaults():
    cfg = config_from_dict({})
    assert cfg.window_seconds == 300


# ---------------------------------------------------------------------------
# RequestDeduplicator
# ---------------------------------------------------------------------------

def test_new_request_not_duplicate():
    dedup = RequestDeduplicator(DedupConfig())
    assert dedup.is_duplicate("req-1") is False


def test_recorded_request_is_duplicate():
    dedup = RequestDeduplicator(DedupConfig())
    dedup.record("req-1")
    assert dedup.is_duplicate("req-1") is True


def test_expired_entry_not_duplicate():
    cfg = DedupConfig(window_seconds=1)
    dedup = RequestDeduplicator(cfg)
    dedup.record("req-old")
    # Manually backdate the timestamp
    dedup._seen["req-old"] = time.monotonic() - 2
    assert dedup.is_duplicate("req-old") is False


def test_max_entries_evicts_oldest():
    cfg = DedupConfig(max_entries=3)
    dedup = RequestDeduplicator(cfg)
    for i in range(3):
        dedup.record(f"req-{i}")
        time.sleep(0.001)  # ensure distinct monotonic timestamps
    dedup.record("req-new")
    assert dedup.size() == 3
    assert dedup.is_duplicate("req-new") is True


def test_size_excludes_expired():
    cfg = DedupConfig(window_seconds=1)
    dedup = RequestDeduplicator(cfg)
    dedup.record("a")
    dedup._seen["a"] = time.monotonic() - 5
    assert dedup.size() == 0


# ---------------------------------------------------------------------------
# check_dedup_for_route
# ---------------------------------------------------------------------------

def _make_route(dedup_cfg=None):
    r = types.SimpleNamespace(id="route-abc", dedup=dedup_cfg)
    return r


def test_check_dedup_no_config_returns_false():
    route = _make_route(dedup_cfg=None)
    is_dup, cfg = check_dedup_for_route(route, "req-1")
    assert is_dup is False
    assert cfg is None


def test_check_dedup_first_request_not_duplicate():
    route = _make_route(dedup_cfg={"window_seconds": 60})
    is_dup, cfg = check_dedup_for_route(route, "req-1")
    assert is_dup is False
    assert cfg is not None


def test_check_dedup_second_request_is_duplicate():
    route = _make_route(dedup_cfg={"window_seconds": 60})
    check_dedup_for_route(route, "req-1")
    is_dup, _ = check_dedup_for_route(route, "req-1")
    assert is_dup is True


def test_check_dedup_no_request_id_returns_false():
    route = _make_route(dedup_cfg={"window_seconds": 60})
    is_dup, _ = check_dedup_for_route(route, None)
    assert is_dup is False


# ---------------------------------------------------------------------------
# build_dedup_response
# ---------------------------------------------------------------------------

def test_build_dedup_response_contains_request_id():
    resp = build_dedup_response("req-xyz")
    assert resp["request_id"] == "req-xyz"
    assert resp["error"] == "duplicate_request"


# ---------------------------------------------------------------------------
# Handler routes
# ---------------------------------------------------------------------------

def _make_handler(path: str, method: str = "GET"):
    buf = BytesIO()

    @add_dedup_routes
    class Handler:
        def __init__(self):
            self.path = path
            self.wfile = buf
            self._response = None
            self._headers = {}

        def send_response(self, code):
            self._response = code

        def send_header(self, k, v):
            self._headers[k] = v

        def end_headers(self):
            pass

        def log_message(self, *a):
            pass

    h = Handler()
    return h, buf


def test_get_dedup_all_empty():
    h, buf = _make_handler("/dedup")
    h.do_GET()
    assert h._response == 200
    data = json.loads(buf.getvalue())
    assert data == {}


def test_get_dedup_all_with_entry():
    cfg = DedupConfig()
    d = get_deduplicator("my-route", cfg)
    d.record("r1")
    h, buf = _make_handler("/dedup")
    h.do_GET()
    data = json.loads(buf.getvalue())
    assert "my-route" in data
    assert data["my-route"]["tracked_ids"] == 1


def test_get_dedup_route_not_found():
    h, buf = _make_handler("/dedup/missing")
    h.do_GET()
    assert h._response == 404


def test_get_dedup_route_found():
    cfg = DedupConfig()
    get_deduplicator("r1", cfg).record("x")
    h, buf = _make_handler("/dedup/r1")
    h.do_GET()
    assert h._response == 200
    data = json.loads(buf.getvalue())
    assert data["tracked_ids"] == 1


def test_delete_dedup_route_clears_it():
    cfg = DedupConfig()
    get_deduplicator("r2", cfg).record("y")
    h, buf = _make_handler("/dedup/r2")
    h.do_DELETE()
    assert h._response == 200
    assert "r2" not in _dedup_registry


def test_delete_dedup_route_not_found():
    h, buf = _make_handler("/dedup/ghost")
    h.do_DELETE()
    assert h._response == 404
