"""Dispatcher: wires together filtering, transformation, and relaying."""

import logging
from typing import Any

from hookbridge.config import RouteConfig
from hookbridge.filter import matches_filters
from hookbridge.transform import transform_payload
from hookbridge.relay import relay_payload, RelayError

logger = logging.getLogger(__name__)


class DispatchResult:
    """Outcome of a single route dispatch attempt."""

    def __init__(
        self,
        route_name: str,
        skipped: bool = False,
        success: bool = False,
        status_code: int | None = None,
        error: str | None = None,
    ):
        self.route_name = route_name
        self.skipped = skipped
        self.success = success
        self.status_code = status_code
        self.error = error

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"DispatchResult(route={self.route_name!r}, skipped={self.skipped}, "
            f"success={self.success}, status_code={self.status_code})"
        )


def dispatch(route: RouteConfig, raw_payload: dict[str, Any]) -> DispatchResult:
    """Apply filters and transformations for *route*, then relay the payload.

    Returns a :class:`DispatchResult` describing the outcome.
    """
    name = route.name

    if route.filters and not matches_filters(raw_payload, route.filters):
        logger.debug("Route %r: payload did not match filters — skipping.", name)
        return DispatchResult(route_name=name, skipped=True)

    outgoing = transform_payload(raw_payload, route.transform) if route.transform else raw_payload

    try:
        response = relay_payload(
            target_url=route.target,
            payload=outgoing,
            headers=route.headers,
            retries=route.retries,
        )
        return DispatchResult(
            route_name=name,
            success=True,
            status_code=response.status_code,
        )
    except RelayError as exc:
        logger.error("Route %r relay failed: %s", name, exc)
        return DispatchResult(
            route_name=name,
            success=False,
            status_code=exc.status_code,
            error=str(exc),
        )


def dispatch_all(
    routes: list[RouteConfig], raw_payload: dict[str, Any]
) -> list[DispatchResult]:
    """Dispatch *raw_payload* across every route in *routes*."""
    return [dispatch(route, raw_payload) for route in routes]


def summarise_results(results: list[DispatchResult]) -> dict[str, int]:
    """Return a count summary of *results* by outcome category.

    Keys in the returned dict:
    - ``"success"``  — routes that relayed successfully.
    - ``"skipped"``  — routes whose filters did not match.
    - ``"failed"``   — routes that encountered a relay error.
    """
    summary: dict[str, int] = {"success": 0, "skipped": 0, "failed": 0}
    for result in results:
        if result.skipped:
            summary["skipped"] += 1
        elif result.success:
            summary["success"] += 1
        else:
            summary["failed"] += 1
    return summary
