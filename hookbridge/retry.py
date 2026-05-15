"""Retry policy configuration and execution for webhook relay."""

import time
import logging
from dataclasses import dataclass, field
from typing import Callable, Any, Optional

logger = logging.getLogger(__name__)


@dataclass
class RetryPolicy:
    max_attempts: int = 3
    backoff_base: float = 0.5
    backoff_max: float = 10.0
    backoff_factor: float = 2.0
    retry_on: tuple = (500, 502, 503, 504)

    def delay_for(self, attempt: int) -> float:
        """Compute exponential backoff delay for a given attempt (0-indexed)."""
        delay = self.backoff_base * (self.backoff_factor ** attempt)
        return min(delay, self.backoff_max)


@dataclass
class RetryResult:
    success: bool
    attempts: int
    last_exception: Optional[Exception] = None
    last_status: Optional[int] = None
    value: Any = None


def with_retry(
    fn: Callable[[], Any],
    policy: RetryPolicy,
    should_retry: Optional[Callable[[Any], bool]] = None,
    sleep_fn: Callable[[float], None] = time.sleep,
) -> RetryResult:
    """Execute fn with retry logic defined by policy.

    Args:
        fn: Callable that returns a result or raises an exception.
        policy: RetryPolicy controlling retry behaviour.
        should_retry: Optional callable that receives fn's return value and
            returns True if a retry should be attempted.
        sleep_fn: Injectable sleep function (useful for testing).
    """
    last_exc = None
    last_val = None

    for attempt in range(policy.max_attempts):
        try:
            result = fn()
            if should_retry and should_retry(result):
                last_val = result
                logger.debug("Retry %d/%d: retryable result", attempt + 1, policy.max_attempts)
                if attempt < policy.max_attempts - 1:
                    sleep_fn(policy.delay_for(attempt))
                continue
            return RetryResult(success=True, attempts=attempt + 1, value=result)
        except Exception as exc:
            last_exc = exc
            logger.debug("Retry %d/%d: %s", attempt + 1, policy.max_attempts, exc)
            if attempt < policy.max_attempts - 1:
                sleep_fn(policy.delay_for(attempt))

    return RetryResult(
        success=False,
        attempts=policy.max_attempts,
        last_exception=last_exc,
        last_status=getattr(last_val, "status", None),
        value=last_val,
    )
