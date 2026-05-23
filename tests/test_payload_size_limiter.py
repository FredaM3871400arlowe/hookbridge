"""Tests for hookbridge.payload_size_limiter."""

import pytest

from hookbridge.payload_size_limiter import (
    SizeLimitConfig,
    config_from_dict,
    get_route_size_limit,
    check_payload_size,
    build_size_limit_response,
    run_size_check_for_route,
    _DEFAULT_MAX_BYTES,
)


# ---------------------------------------------------------------------------
# SizeLimitConfig
# ---------------------------------------------------------------------------

def test_default_max_bytes():
    cfg = SizeLimitConfig()
    assert cfg.max_bytes == _DEFAULT_MAX_BYTES


def test_custom_max_bytes():
    cfg = SizeLimitConfig(max_bytes=4096)
    assert cfg.max_bytes == 4096


def test_max_bytes_below_minimum_raises():
    with pytest.raises(ValueError, match="at least"):
        SizeLimitConfig(max_bytes=10)


def test_max_bytes_above_maximum_raises():
    with pytest.raises(ValueError, match="at most"):
        SizeLimitConfig(max_bytes=100 * 1024 * 1024)


def test_max_bytes_at_minimum_boundary():
    cfg = SizeLimitConfig(max_bytes=64)
    assert cfg.max_bytes == 64


# ---------------------------------------------------------------------------
# config_from_dict
# ---------------------------------------------------------------------------

def test_config_from_dict_uses_max_bytes():
    cfg = config_from_dict({"max_bytes": 8192})
    assert cfg.max_bytes == 8192


def test_config_from_dict_defaults_when_missing():
    cfg = config_from_dict({})
    assert cfg.max_bytes == _DEFAULT_MAX_BYTES


# ---------------------------------------------------------------------------
# get_route_size_limit
# ---------------------------------------------------------------------------

class _Route:
    def __init__(self, size_limit=None):
        self.size_limit = size_limit


def test_get_route_size_limit_none_when_absent():
    route = _Route()
    assert get_route_size_limit(route) is None


def test_get_route_size_limit_passthrough_config_instance():
    cfg = SizeLimitConfig(max_bytes=512)
    route = _Route(size_limit=cfg)
    result = get_route_size_limit(route)
    assert result is cfg


def test_get_route_size_limit_from_dict():
    route = _Route(size_limit={"max_bytes": 2048})
    result = get_route_size_limit(route)
    assert result is not None
    assert result.max_bytes == 2048


# ---------------------------------------------------------------------------
# check_payload_size
# ---------------------------------------------------------------------------

def test_check_payload_size_within_limit_returns_none():
    cfg = SizeLimitConfig(max_bytes=100)
    assert check_payload_size(b"x" * 100, cfg) is None


def test_check_payload_size_over_limit_returns_message():
    cfg = SizeLimitConfig(max_bytes=100)
    result = check_payload_size(b"x" * 101, cfg)
    assert result is not None
    assert "101" in result
    assert "100" in result


def test_check_payload_size_empty_body_allowed():
    cfg = SizeLimitConfig(max_bytes=100)
    assert check_payload_size(b"", cfg) is None


# ---------------------------------------------------------------------------
# build_size_limit_response
# ---------------------------------------------------------------------------

def test_build_size_limit_response_structure():
    resp = build_size_limit_response("too big")
    assert resp["error"] == "payload_too_large"
    assert "too big" in resp["message"]


# ---------------------------------------------------------------------------
# run_size_check_for_route
# ---------------------------------------------------------------------------

def test_run_size_check_no_config_returns_none():
    route = _Route()
    assert run_size_check_for_route(route, b"hello") is None


def test_run_size_check_within_limit_returns_none():
    route = _Route(size_limit={"max_bytes": 256})
    assert run_size_check_for_route(route, b"x" * 256) is None


def test_run_size_check_over_limit_returns_error():
    route = _Route(size_limit={"max_bytes": 256})
    result = run_size_check_for_route(route, b"x" * 257)
    assert result is not None
    assert result["error"] == "payload_too_large"
