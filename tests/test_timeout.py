"""Tests for hookbridge.timeout."""

import pytest

from hookbridge.timeout import (
    DEFAULT_TIMEOUT_SECONDS,
    MAX_TIMEOUT_SECONDS,
    MIN_TIMEOUT_SECONDS,
    TimeoutConfig,
    config_from_dict,
    get_route_timeout,
)


# ---------------------------------------------------------------------------
# TimeoutConfig
# ---------------------------------------------------------------------------


def test_default_timeout():
    cfg = TimeoutConfig()
    assert cfg.seconds == DEFAULT_TIMEOUT_SECONDS


def test_custom_timeout():
    cfg = TimeoutConfig(seconds=30.0)
    assert cfg.seconds == 30.0


def test_timeout_below_minimum_raises():
    with pytest.raises(ValueError, match="Timeout must be between"):
        TimeoutConfig(seconds=0.1)


def test_timeout_above_maximum_raises():
    with pytest.raises(ValueError, match="Timeout must be between"):
        TimeoutConfig(seconds=200.0)


def test_timeout_at_boundary_values():
    assert TimeoutConfig(seconds=MIN_TIMEOUT_SECONDS).seconds == MIN_TIMEOUT_SECONDS
    assert TimeoutConfig(seconds=MAX_TIMEOUT_SECONDS).seconds == MAX_TIMEOUT_SECONDS


# ---------------------------------------------------------------------------
# config_from_dict
# ---------------------------------------------------------------------------


def test_config_from_empty_dict_returns_default():
    cfg = config_from_dict({})
    assert cfg.seconds == DEFAULT_TIMEOUT_SECONDS


def test_config_from_none_returns_default():
    cfg = config_from_dict(None)
    assert cfg.seconds == DEFAULT_TIMEOUT_SECONDS


def test_config_from_flat_shorthand():
    cfg = config_from_dict({"timeout_seconds": 7})
    assert cfg.seconds == 7.0


def test_config_from_nested_block():
    cfg = config_from_dict({"timeout": {"seconds": 15}})
    assert cfg.seconds == 15.0


def test_config_from_nested_block_missing_seconds_uses_default():
    cfg = config_from_dict({"timeout": {}})
    assert cfg.seconds == DEFAULT_TIMEOUT_SECONDS


def test_config_flat_shorthand_takes_precedence_over_nested():
    # If both keys are present, flat shorthand wins.
    cfg = config_from_dict({"timeout_seconds": 5, "timeout": {"seconds": 20}})
    assert cfg.seconds == 5.0


def test_config_from_dict_invalid_value_raises():
    with pytest.raises(ValueError):
        config_from_dict({"timeout_seconds": 999})


# ---------------------------------------------------------------------------
# get_route_timeout
# ---------------------------------------------------------------------------


class _FakeRoute:
    def __init__(self, options=None):
        self.options = options


def test_get_route_timeout_no_options_returns_default():
    route = _FakeRoute(options=None)
    cfg = get_route_timeout(route)
    assert cfg.seconds == DEFAULT_TIMEOUT_SECONDS


def test_get_route_timeout_with_flat_option():
    route = _FakeRoute(options={"timeout_seconds": 25})
    cfg = get_route_timeout(route)
    assert cfg.seconds == 25.0


def test_get_route_timeout_with_nested_option():
    route = _FakeRoute(options={"timeout": {"seconds": 8}})
    cfg = get_route_timeout(route)
    assert cfg.seconds == 8.0


def test_get_route_timeout_missing_attribute_returns_default():
    class _Bare:
        pass

    cfg = get_route_timeout(_Bare())
    assert cfg.seconds == DEFAULT_TIMEOUT_SECONDS
