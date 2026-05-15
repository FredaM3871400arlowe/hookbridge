"""Tests for hookbridge.rate_limiter and hookbridge.rate_limit_middleware."""

import time
import pytest

from hookbridge.rate_limiter import (
    BucketState,
    RateLimitConfig,
    RateLimiter,
    parse_rate_limit,
)
from hookbridge.rate_limit_middleware import (
    build_rate_limit_response,
    check_rate_limit,
)


@pytest.fixture()
def limiter() -> RateLimiter:
    return RateLimiter()


@pytest.fixture()
def cfg() -> RateLimitConfig:
    return RateLimitConfig(requests=3, window_seconds=60)


# ---------------------------------------------------------------------------
# RateLimiter unit tests
# ---------------------------------------------------------------------------

def test_allows_requests_within_limit(limiter, cfg):
    for _ in range(3):
        assert limiter.is_allowed("/hook", cfg) is True


def test_blocks_request_over_limit(limiter, cfg):
    for _ in range(3):
        limiter.is_allowed("/hook", cfg)
    assert limiter.is_allowed("/hook", cfg) is False


def test_window_reset_allows_new_requests(limiter, cfg):
    for _ in range(3):
        limiter.is_allowed("/hook", cfg)
    assert limiter.is_allowed("/hook", cfg) is False

    # Simulate window expiry by passing a future timestamp
    future = time.monotonic() + cfg.window_seconds + 1
    assert limiter.is_allowed("/hook", cfg, now=future) is True


def test_different_routes_are_independent(limiter, cfg):
    for _ in range(3):
        limiter.is_allowed("/a", cfg)
    # /a is exhausted but /b should still be allowed
    assert limiter.is_allowed("/a", cfg) is False
    assert limiter.is_allowed("/b", cfg) is True


def test_reset_clears_bucket(limiter, cfg):
    for _ in range(3):
        limiter.is_allowed("/hook", cfg)
    limiter.reset("/hook")
    assert limiter.is_allowed("/hook", cfg) is True


# ---------------------------------------------------------------------------
# parse_rate_limit tests
# ---------------------------------------------------------------------------

def test_parse_rate_limit_returns_config():
    route = {"rate_limit": {"requests": 10, "window_seconds": 30}}
    cfg = parse_rate_limit(route)
    assert cfg is not None
    assert cfg.requests == 10
    assert cfg.window_seconds == 30


def test_parse_rate_limit_returns_none_when_missing():
    assert parse_rate_limit({}) is None
    assert parse_rate_limit({"rate_limit": None}) is None


# ---------------------------------------------------------------------------
# Middleware tests
# ---------------------------------------------------------------------------

def test_check_rate_limit_no_config_always_passes():
    assert check_rate_limit("/hook", None) is True


def test_check_rate_limit_delegates_to_limiter(limiter, cfg):
    for _ in range(cfg.requests):
        assert check_rate_limit("/hook", cfg, limiter=limiter) is True
    assert check_rate_limit("/hook", cfg, limiter=limiter) is False


def test_build_rate_limit_response_shape():
    cfg = RateLimitConfig(requests=5, window_seconds=10)
    resp = build_rate_limit_response("/hook", cfg)
    assert resp["error"] == "rate_limit_exceeded"
    assert resp["route"] == "/hook"
    assert resp["limit"] == 5
    assert resp["window_seconds"] == 10
