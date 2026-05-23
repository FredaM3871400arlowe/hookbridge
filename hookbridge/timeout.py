"""Per-route request timeout configuration and enforcement."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


DEFAULT_TIMEOUT_SECONDS: float = 10.0
MIN_TIMEOUT_SECONDS: float = 0.5
MAX_TIMEOUT_SECONDS: float = 120.0


@dataclass(frozen=True)
class TimeoutConfig:
    """Timeout settings for a single route."""

    seconds: float = DEFAULT_TIMEOUT_SECONDS

    def __post_init__(self) -> None:
        if not (MIN_TIMEOUT_SECONDS <= self.seconds <= MAX_TIMEOUT_SECONDS):
            raise ValueError(
                f"Timeout must be between {MIN_TIMEOUT_SECONDS} and "
                f"{MAX_TIMEOUT_SECONDS} seconds, got {self.seconds}"
            )


def config_from_dict(data: dict) -> TimeoutConfig:
    """Parse a TimeoutConfig from a raw config dictionary.

    Accepts either a top-level ``timeout_seconds`` float or a nested
    ``timeout`` object with a ``seconds`` key.
    """
    if not data:
        return TimeoutConfig()

    # Support flat shorthand: {"timeout_seconds": 5}
    if "timeout_seconds" in data:
        return TimeoutConfig(seconds=float(data["timeout_seconds"]))

    # Support nested block: {"timeout": {"seconds": 5}}
    block = data.get("timeout")
    if isinstance(block, dict):
        return TimeoutConfig(seconds=float(block.get("seconds", DEFAULT_TIMEOUT_SECONDS)))

    return TimeoutConfig()


def get_route_timeout(route) -> TimeoutConfig:
    """Extract a TimeoutConfig from a RouteConfig-like object.

    Falls back to the global default when no timeout is configured.
    """
    raw: Optional[dict] = getattr(route, "options", None) or {}
    return config_from_dict(raw)
