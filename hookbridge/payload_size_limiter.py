"""Payload size limiting middleware for hookbridge."""

from dataclasses import dataclass, field
from typing import Optional

_DEFAULT_MAX_BYTES = 1 * 1024 * 1024  # 1 MB
_MINIMUM_MAX_BYTES = 64
_MAXIMUM_MAX_BYTES = 50 * 1024 * 1024  # 50 MB


@dataclass
class SizeLimitConfig:
    max_bytes: int = _DEFAULT_MAX_BYTES

    def __post_init__(self) -> None:
        if self.max_bytes < _MINIMUM_MAX_BYTES:
            raise ValueError(
                f"max_bytes must be at least {_MINIMUM_MAX_BYTES}, got {self.max_bytes}"
            )
        if self.max_bytes > _MAXIMUM_MAX_BYTES:
            raise ValueError(
                f"max_bytes must be at most {_MAXIMUM_MAX_BYTES}, got {self.max_bytes}"
            )


def config_from_dict(data: dict) -> SizeLimitConfig:
    """Build a SizeLimitConfig from a raw config dictionary."""
    return SizeLimitConfig(
        max_bytes=int(data.get("max_bytes", _DEFAULT_MAX_BYTES))
    )


def get_route_size_limit(route) -> Optional[SizeLimitConfig]:
    """Extract SizeLimitConfig from a RouteConfig, or None if not configured."""
    raw = getattr(route, "size_limit", None)
    if raw is None:
        return None
    if isinstance(raw, SizeLimitConfig):
        return raw
    return config_from_dict(raw)


def check_payload_size(body: bytes, config: SizeLimitConfig) -> Optional[str]:
    """Return an error message if body exceeds the configured limit, else None."""
    if len(body) > config.max_bytes:
        return (
            f"Payload size {len(body)} bytes exceeds limit of "
            f"{config.max_bytes} bytes."
        )
    return None


def build_size_limit_response(message: str) -> dict:
    """Build a structured error response for an oversized payload."""
    return {
        "error": "payload_too_large",
        "message": message,
    }


def run_size_check_for_route(route, body: bytes) -> Optional[dict]:
    """Run size check for the given route.  Returns error dict or None."""
    cfg = get_route_size_limit(route)
    if cfg is None:
        return None
    error_msg = check_payload_size(body, cfg)
    if error_msg:
        return build_size_limit_response(error_msg)
    return None
