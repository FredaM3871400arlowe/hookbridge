"""Wraps RelayError-raising relay calls with the retry subsystem."""

import logging
from typing import Any, Optional

from hookbridge.relay import RelayError
from hookbridge.retry import RetryPolicy, with_retry, RetryResult

logger = logging.getLogger(__name__)


def _is_retryable_status(exc: Exception, policy: RetryPolicy) -> bool:
    status = getattr(exc, "status_code", None)
    if status is None:
        return True  # network-level error — always retry
    return status in policy.retry_on


def relay_with_retry(
    relay_fn,
    url: str,
    payload: Any,
    headers: Optional[dict],
    policy: RetryPolicy,
    sleep_fn=None,
) -> RetryResult:
    """Call relay_fn(url, payload, headers) with retry logic.

    relay_fn should raise RelayError on failure.
    Returns a RetryResult; callers should inspect .success and .last_exception.
    """
    import time
    _sleep = sleep_fn or time.sleep

    last_exc_holder = []

    def attempt():
        try:
            relay_fn(url, payload, headers)
            return True
        except RelayError as exc:
            last_exc_holder.append(exc)
            if not _is_retryable_status(exc, policy):
                raise  # non-retryable: bubble up immediately
            raise

    result = with_retry(attempt, policy, sleep_fn=_sleep)

    if not result.success and last_exc_holder:
        result.last_exception = last_exc_holder[-1]

    return result
