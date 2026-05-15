"""Tests for hookbridge.retry and hookbridge.retry_config."""

import pytest
from unittest.mock import MagicMock, call
from hookbridge.retry import RetryPolicy, RetryResult, with_retry
from hookbridge.retry_config import policy_from_dict, get_route_policy, DEFAULT_POLICY


# ---------------------------------------------------------------------------
# RetryPolicy
# ---------------------------------------------------------------------------

def test_delay_for_exponential():
    policy = RetryPolicy(backoff_base=1.0, backoff_factor=2.0, backoff_max=100.0)
    assert policy.delay_for(0) == 1.0
    assert policy.delay_for(1) == 2.0
    assert policy.delay_for(2) == 4.0


def test_delay_for_capped_at_max():
    policy = RetryPolicy(backoff_base=1.0, backoff_factor=10.0, backoff_max=5.0)
    assert policy.delay_for(3) == 5.0


# ---------------------------------------------------------------------------
# with_retry — success on first attempt
# ---------------------------------------------------------------------------

def test_with_retry_success_first_attempt():
    fn = MagicMock(return_value="ok")
    sleep = MagicMock()
    result = with_retry(fn, RetryPolicy(max_attempts=3), sleep_fn=sleep)

    assert result.success is True
    assert result.attempts == 1
    assert result.value == "ok"
    sleep.assert_not_called()


# ---------------------------------------------------------------------------
# with_retry — retries on exception
# ---------------------------------------------------------------------------

def test_with_retry_retries_on_exception():
    fn = MagicMock(side_effect=[ValueError("fail"), ValueError("fail"), "ok"])
    sleep = MagicMock()
    policy = RetryPolicy(max_attempts=3, backoff_base=0.1)
    result = with_retry(fn, policy, sleep_fn=sleep)

    assert result.success is True
    assert result.attempts == 3
    assert sleep.call_count == 2


def test_with_retry_exhausted_returns_failure():
    fn = MagicMock(side_effect=RuntimeError("boom"))
    sleep = MagicMock()
    policy = RetryPolicy(max_attempts=3, backoff_base=0.0)
    result = with_retry(fn, policy, sleep_fn=sleep)

    assert result.success is False
    assert result.attempts == 3
    assert isinstance(result.last_exception, RuntimeError)


# ---------------------------------------------------------------------------
# with_retry — should_retry callback
# ---------------------------------------------------------------------------

def test_with_retry_should_retry_callback():
    responses = [503, 503, 200]
    fn = MagicMock(side_effect=responses)
    sleep = MagicMock()
    policy = RetryPolicy(max_attempts=3, backoff_base=0.0)
    result = with_retry(fn, policy, should_retry=lambda r: r >= 500, sleep_fn=sleep)

    assert result.success is True
    assert result.attempts == 3
    assert result.value == 200


def test_with_retry_should_retry_exhausted():
    fn = MagicMock(return_value=503)
    sleep = MagicMock()
    policy = RetryPolicy(max_attempts=2, backoff_base=0.0)
    result = with_retry(fn, policy, should_retry=lambda r: r >= 500, sleep_fn=sleep)

    assert result.success is False
    assert result.attempts == 2


# ---------------------------------------------------------------------------
# retry_config helpers
# ---------------------------------------------------------------------------

def test_policy_from_dict_overrides():
    data = {"max_attempts": 5, "backoff_base": 1.0, "retry_on": [429, 503]}
    policy = policy_from_dict(data)
    assert policy.max_attempts == 5
    assert policy.backoff_base == 1.0
    assert 429 in policy.retry_on


def test_policy_from_dict_defaults_for_missing_keys():
    policy = policy_from_dict({})
    assert policy.max_attempts == DEFAULT_POLICY.max_attempts


def test_get_route_policy_uses_route_level():
    route = MagicMock(retry={"max_attempts": 7})
    app = MagicMock(retry={"max_attempts": 2})
    policy = get_route_policy(route, app)
    assert policy.max_attempts == 7


def test_get_route_policy_falls_back_to_app():
    route = MagicMock(retry=None)
    app = MagicMock(retry={"max_attempts": 4})
    policy = get_route_policy(route, app)
    assert policy.max_attempts == 4


def test_get_route_policy_falls_back_to_default():
    route = MagicMock(retry=None)
    app = MagicMock(retry=None)
    policy = get_route_policy(route, app)
    assert policy.max_attempts == DEFAULT_POLICY.max_attempts
