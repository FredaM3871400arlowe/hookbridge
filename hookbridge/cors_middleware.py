"""Middleware helpers for applying CORS headers in the hookbridge server."""

from typing import Optional
from hookbridge.cors import CORSConfig, build_cors_headers, is_preflight


def apply_cors_to_handler(handler, config: Optional[CORSConfig]) -> bool:
    """Attach CORS headers to the current handler response.

    Returns True if the request was a preflight and has been fully handled
    (caller should not process further), False otherwise.
    """
    if config is None:
        return False

    request_origin = _get_origin(handler)
    cors_headers = build_cors_headers(config, request_origin)

    method = handler.command
    raw_headers = {k: v for k, v in handler.headers.items()}

    if is_preflight(method, raw_headers):
        handler.send_response(204)
        for key, value in cors_headers.items():
            handler.send_header(key, value)
        handler.end_headers()
        return True

    # Store headers for later attachment (called after send_response in do_POST/do_GET)
    handler._pending_cors_headers = cors_headers
    return False


def flush_cors_headers(handler) -> None:
    """Write any pending CORS headers queued by apply_cors_to_handler."""
    pending = getattr(handler, "_pending_cors_headers", {})
    for key, value in pending.items():
        handler.send_header(key, value)
    handler._pending_cors_headers = {}


def _get_origin(handler) -> Optional[str]:
    """Extract the Origin header value from the request, case-insensitively."""
    for key, value in handler.headers.items():
        if key.lower() == "origin":
            return value
    return None
