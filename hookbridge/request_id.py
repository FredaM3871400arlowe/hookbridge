"""Request ID middleware: generates and attaches a unique request ID to each incoming request."""

import uuid
from typing import Optional

_HEADER_NAME = "X-Request-ID"
_GENERATED_PREFIX = "hb-"


def generate_request_id() -> str:
    """Generate a new unique request ID."""
    return f"{_GENERATED_PREFIX}{uuid.uuid4().hex}"


def extract_request_id(headers: dict) -> Optional[str]:
    """Extract an existing request ID from headers, case-insensitively."""
    for key, value in headers.items():
        if key.lower() == _HEADER_NAME.lower():
            return value
    return None


def resolve_request_id(headers: dict) -> tuple[str, bool]:
    """Return (request_id, was_generated).

    If the incoming headers already contain a request ID, reuse it.
    Otherwise generate a new one.
    """
    existing = extract_request_id(headers)
    if existing:
        return existing, False
    return generate_request_id(), True


def attach_request_id_header(response_headers: list[tuple[str, str]], request_id: str) -> None:
    """Append the X-Request-ID header to a mutable list of (name, value) tuples."""
    response_headers.append((_HEADER_NAME, request_id))


def build_request_id_context(headers: dict) -> dict:
    """Build a context dict with request_id and generated flag."""
    request_id, generated = resolve_request_id(headers)
    return {
        "request_id": request_id,
        "generated": generated,
        "header_name": _HEADER_NAME,
    }
