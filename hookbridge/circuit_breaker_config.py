"""Helpers to build CircuitBreakerConfig from route/app config dicts."""

from __future__ import annotations

from typing import Any, Dict, Optional

from hookbridge.circuit_breaker import CircuitBreaker, CircuitBreakerConfig

_DEFAULT_CONFIG = CircuitBreakerConfig()


def config_from_dict(d: Dict[str, Any]) -> CircuitBreakerConfig:
    """Build a CircuitBreakerConfig from a plain dict (e.g. parsed JSON)."""
    return CircuitBreakerConfig(
        failure_threshold=int(d.get("failure_threshold", _DEFAULT_CONFIG.failure_threshold)),
        recovery_timeout=float(d.get("recovery_timeout", _DEFAULT_CONFIG.recovery_timeout)),
        success_threshold=int(d.get("success_threshold", _DEFAULT_CONFIG.success_threshold)),
    )


def get_route_breaker_config(
    route_cfg: Dict[str, Any],
    app_cfg: Optional[Dict[str, Any]] = None,
) -> CircuitBreakerConfig:
    """Return CircuitBreakerConfig for a route, falling back to app-level defaults."""
    route_cb = route_cfg.get("circuit_breaker")
    if route_cb:
        return config_from_dict(route_cb)
    if app_cfg:
        app_cb = app_cfg.get("circuit_breaker")
        if app_cb:
            return config_from_dict(app_cb)
    return _DEFAULT_CONFIG


def build_circuit_breaker(
    route_cfg: Dict[str, Any],
    app_cfg: Optional[Dict[str, Any]] = None,
) -> CircuitBreaker:
    """Convenience: build a CircuitBreaker wired to the resolved config."""
    cfg = get_route_breaker_config(route_cfg, app_cfg)
    return CircuitBreaker(config=cfg)
