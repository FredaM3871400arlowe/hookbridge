"""JSON Schema-based payload validation for incoming webhook routes."""

import json
import jsonschema
from typing import Optional


class ValidationError(Exception):
    """Raised when a payload fails schema validation."""

    def __init__(self, message: str, path: str = ""):
        super().__init__(message)
        self.path = path


def validate_payload(payload: dict, schema: dict) -> Optional[ValidationError]:
    """Validate *payload* against *schema*.

    Returns ``None`` on success or a :class:`ValidationError` on failure.
    """
    try:
        jsonschema.validate(instance=payload, schema=schema)
        return None
    except jsonschema.ValidationError as exc:
        path = "/".join(str(p) for p in exc.absolute_path) if exc.absolute_path else ""
        return ValidationError(exc.message, path=path)
    except jsonschema.SchemaError as exc:
        return ValidationError(f"Invalid schema definition: {exc.message}")


def get_route_schema(route_cfg: dict) -> Optional[dict]:
    """Extract the optional ``payload_schema`` from a route config dict."""
    return route_cfg.get("payload_schema")


def check_payload_for_route(payload: dict, route_cfg: dict) -> Optional[ValidationError]:
    """Return a :class:`ValidationError` if the route defines a schema and
    *payload* does not satisfy it, otherwise ``None``."""
    schema = get_route_schema(route_cfg)
    if schema is None:
        return None
    return validate_payload(payload, schema)


def build_validation_response(error: ValidationError) -> dict:
    """Build a JSON-serialisable error response body for a validation failure."""
    body: dict = {"error": "payload_validation_failed", "detail": str(error)}
    if error.path:
        body["path"] = error.path
    return body
