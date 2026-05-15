"""Tests for relay_retry integration layer."""

import pytest
from unittest.mock import MagicMock, patch
from hookbridge.relay import RelayError
from hookbridge.retry import RetryPolicy
from hookbridge.relay_retry import relay_with_retry


URL = "https://example.com/hook"
PAYLOAD = {"event": "push"}
HEADERS = {"X-Test": "1"}


def make_policy(**kwargs):
    defaults = dict(max_attempts=3, backoff_base=0.0, retry_on=(500, 502, 503))
    defaults.update(kwargs)
    return RetryPolicy(**defaults)


def test_relay_with_retry_success_first_attempt():
    fn = MagicMock(return_value=None)
    result = relay_with_retry(fn, URL, PAYLOAD, HEADERS, make_policy(), sleep_fn=MagicMock())
    assert result.success is True
    assert result.attempts == 1
    fn.assert_called_once_with(URL, PAYLOAD, HEADERS)


def test_relay_with_retry_retries_on_server_error():
    err = RelayError("server error")
    err.status_code = 503
    fn = MagicMock(side_effect=[err, err, None])
    sleep = MagicMock()
    result = relay_with_retry(fn, URL, PAYLOAD, HEADERS, make_policy(), sleep_fn=sleep)
    assert result.success is True
    assert result.attempts == 3
    assert sleep.call_count == 2


def test_relay_with_retry_exhausted_returns_failure():
    err = RelayError("gone")
    err.status_code = 503
    fn = MagicMock(side_effect=err)
    result = relay_with_retry(fn, URL, PAYLOAD, HEADERS, make_policy(max_attempts=2), sleep_fn=MagicMock())
    assert result.success is False
    assert result.attempts == 2
    assert isinstance(result.last_exception, RelayError)


def test_relay_with_retry_non_retryable_bubbles_immediately():
    err = RelayError("not found")
    err.status_code = 404  # not in retry_on
    fn = MagicMock(side_effect=err)
    with pytest.raises(RelayError):
        relay_with_retry(fn, URL, PAYLOAD, HEADERS, make_policy(), sleep_fn=MagicMock())
    assert fn.call_count == 1


def test_relay_with_retry_network_error_retries():
    fn = MagicMock(side_effect=[RelayError("timeout"), None])
    # RelayError with no status_code attribute — treated as network error
    sleep = MagicMock()
    result = relay_with_retry(fn, URL, PAYLOAD, HEADERS, make_policy(max_attempts=3), sleep_fn=sleep)
    assert result.success is True
    assert result.attempts == 2
