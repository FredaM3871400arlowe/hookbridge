"""Tests for hookbridge.circuit_breaker and hookbridge.circuit_breaker_config."""

from __future__ import annotations

import time

import pytest

from hookbridge.circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerConfig,
    CircuitState,
)
from hookbridge.circuit_breaker_config import config_from_dict, get_route_breaker_config


@pytest.fixture()
def cb() -> CircuitBreaker:
    cfg = CircuitBreakerConfig(failure_threshold=3, recovery_timeout=1.0, success_threshold=2)
    return CircuitBreaker(config=cfg)


def test_initial_state_is_closed(cb: CircuitBreaker) -> None:
    assert cb.get_state("r1").state == CircuitState.CLOSED


def test_allows_requests_when_closed(cb: CircuitBreaker) -> None:
    assert cb.is_allowed("r1") is True


def test_opens_after_threshold_failures(cb: CircuitBreaker) -> None:
    for _ in range(3):
        cb.record_failure("r1")
    assert cb.get_state("r1").state == CircuitState.OPEN


def test_blocks_when_open(cb: CircuitBreaker) -> None:
    for _ in range(3):
        cb.record_failure("r1")
    assert cb.is_allowed("r1") is False


def test_transitions_to_half_open_after_timeout(cb: CircuitBreaker) -> None:
    for _ in range(3):
        cb.record_failure("r1")
    # Manually wind back opened_at
    cb._routes["r1"].opened_at = time.monotonic() - 2.0
    assert cb.is_allowed("r1") is True
    assert cb.get_state("r1").state == CircuitState.HALF_OPEN


def test_closes_after_success_threshold_in_half_open(cb: CircuitBreaker) -> None:
    for _ in range(3):
        cb.record_failure("r1")
    cb._routes["r1"].opened_at = time.monotonic() - 2.0
    cb.is_allowed("r1")  # triggers HALF_OPEN
    cb.record_success("r1")
    cb.record_success("r1")
    assert cb.get_state("r1").state == CircuitState.CLOSED


def test_reopens_on_failure_in_half_open(cb: CircuitBreaker) -> None:
    for _ in range(3):
        cb.record_failure("r1")
    cb._routes["r1"].opened_at = time.monotonic() - 2.0
    cb.is_allowed("r1")  # triggers HALF_OPEN
    cb.record_failure("r1")
    assert cb.get_state("r1").state == CircuitState.OPEN


def test_reset_restores_closed_state(cb: CircuitBreaker) -> None:
    for _ in range(3):
        cb.record_failure("r1")
    cb.reset("r1")
    assert cb.get_state("r1").state == CircuitState.CLOSED


def test_all_states_returns_dict(cb: CircuitBreaker) -> None:
    cb.record_failure("r1")
    cb.record_failure("r2")
    states = cb.all_states()
    assert "r1" in states and "r2" in states
    assert states["r1"]["failure_count"] == 1


def test_success_resets_failure_count_when_closed(cb: CircuitBreaker) -> None:
    cb.record_failure("r1")
    cb.record_failure("r1")
    cb.record_success("r1")
    assert cb.get_state("r1").failure_count == 0


def test_does_not_open_below_threshold(cb: CircuitBreaker) -> None:
    """Circuit should remain CLOSED when failures are below the threshold."""
    for _ in range(2):  # threshold is 3, so 2 failures should not open
        cb.record_failure("r1")
    assert cb.get_state("r1").state == CircuitState.CLOSED
    assert cb.is_allowed("r1") is True


# --- config helpers ---

def test_config_from_dict_defaults() -> None:
    cfg = config_from_dict({})
    assert cfg.failure_threshold == 5
    assert cfg.recovery_timeout == 30.0
    assert cfg.success_threshold == 2


def test_config_from_dict_custom() -> None:
    cfg = config_from_dict({"failure_threshold": 10, "recovery_timeout": 60.0, "success_threshold": 3})
    assert cfg.failure_threshold == 10
    assert cfg.recovery_timeout == 60.0
    assert cfg.success_threshold == 3
