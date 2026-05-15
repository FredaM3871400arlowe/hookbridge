"""Helpers to build RetryPolicy from route/app configuration dicts."""

from typing import Any, Dict, Optional
from hookbridge.retry import RetryPolicy


DEFAULT_POLICY = RetryPolicy()


def policy_from_dict(data: Dict[str, Any]) -> RetryPolicy:
    """Build a RetryPolicy from a plain dict (e.g. parsed from JSON config)."""
    return RetryPolicy(
        max_attempts=int(data.get("max_attempts", DEFAULT_POLICY.max_attempts)),
        backoff_base=float(data.get("backoff_base", DEFAULT_POLICY.backoff_base)),
        backoff_max=float(data.get("backoff_max", DEFAULT_POLICY.backoff_max)),
        backoff_factor=float(data.get("backoff_factor", DEFAULT_POLICY.backoff_factor)),
        retry_on=tuple(data.get("retry_on", list(DEFAULT_POLICY.retry_on))),
    )


def get_route_policy(route_config: Any, app_config: Any) -> RetryPolicy:
    """Resolve retry policy for a route, falling back to app-level then defaults.

    Priority: route-level retry config > app-level retry config > defaults.
    """
    route_retry = getattr(route_config, "retry", None)
    if route_retry:
        return policy_from_dict(route_retry)

    app_retry = getattr(app_config, "retry", None)
    if app_retry:
        return policy_from_dict(app_retry)

    return DEFAULT_POLICY
