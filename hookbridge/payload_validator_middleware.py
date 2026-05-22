"""Middleware helpers that integrate payload validation into the request flow."""

import json
from typing import Optional

from hookbridge.payload_validator import (
    ValidationError,
    check_payload_for_route,
    build_validation_response,
)


def run_validation_for_route(
    payload: dict,
    route_cfg: dict,
    route_name: str,
) -> Optional[dict]:
    """Run schema validation for *route_cfg*.

    Returns a ready-to-send error response dict (with ``status`` and ``body``
    keys) when validation fails, or ``None`` when the payload is valid (or no
    schema is configured).
    """
    error: Optional[ValidationError] = check_payload_for_route(payload, route_cfg)
    if error is None:
        return None
    body = build_validation_response(error)
    body["route"] = route_name
    return {"status": 422, "body": body}


def validation_response_to_bytes(response: dict) -> bytes:
    """Serialise a validation error response body to UTF-8 JSON bytes."""
    return json.dumps(response["body"]).encode("utf-8")
