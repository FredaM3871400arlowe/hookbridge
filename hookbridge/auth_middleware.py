"""Authentication middleware integration for the webhook server."""

import logging
from typing import Optional

from hookbridge.auth import authenticate_request

logger = logging.getLogger(__name__)


def get_route_secret(route_config: dict) -> Optional[str]:
    """Extract the HMAC secret from a route configuration dict."""
    return route_config.get("secret") or None


def check_auth_for_route(
    route_config: dict,
    body: bytes,
    headers: dict,
) -> tuple[bool, str]:
    """Run authentication check for a specific route.

    Returns (allowed, reason). If the route has no secret configured,
    the request is allowed through unconditionally.
    """
    secret = get_route_secret(route_config)
    signature_header = route_config.get("signature_header", "X-Hub-Signature-256")
    algorithm = route_config.get("signature_algorithm", "sha256")

    allowed, reason = authenticate_request(
        body,
        headers,
        secret=secret,
        signature_header=signature_header,
        algorithm=algorithm,
    )

    if not allowed:
        logger.info(
            "Auth rejected for route '%s': %s",
            route_config.get("path", "<unknown>"),
            reason,
        )

    return allowed, reason


def build_auth_response(reason: str) -> dict:
    """Build a standardised 401 error response payload."""
    return {"error": "unauthorized", "detail": reason}
