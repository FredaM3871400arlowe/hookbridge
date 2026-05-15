"""Middleware helpers that integrate rate limiting into the HTTP handler."""

from typing import Optional

from hookbridge.rate_limiter import RateLimitConfig, RateLimiter, get_limiter


def check_rate_limit(
    route_path: str,
    rate_limit_cfg: Optional[RateLimitConfig],
    limiter: Optional[RateLimiter] = None,
) -> bool:
    """Return True when the request is allowed through, False when rate-limited."""
    if rate_limit_cfg is None:
        return True
    if limiter is None:
        limiter = get_limiter()
    return limiter.is_allowed(route_path, rate_limit_cfg)


def build_rate_limit_response(route_path: str, config: RateLimitConfig) -> dict:
    """Build a JSON-serialisable error body for a 429 response."""
    return {
        "error": "rate_limit_exceeded",
        "route": route_path,
        "limit": config.requests,
        "window_seconds": config.window_seconds,
    }


def get_route_rate_limit(
    route_path: str,
    app_config,
) -> Optional[RateLimitConfig]:
    """Look up the RateLimitConfig for *route_path* from the loaded AppConfig."""
    from hookbridge.rate_limiter import parse_rate_limit

    for route in app_config.routes:
        if route.path == route_path:
            return parse_rate_limit(route.__dict__)
    return None
