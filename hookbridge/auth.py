"""Webhook authentication and signature verification."""

import hashlib
import hmac
import logging
from typing import Optional

logger = logging.getLogger(__name__)


def compute_hmac_signature(secret: str, body: bytes, algorithm: str = "sha256") -> str:
    """Compute HMAC signature for a payload body."""
    key = secret.encode("utf-8")
    mac = hmac.new(key, body, getattr(hashlib, algorithm))
    return f"{algorithm}={mac.hexdigest()}"


def verify_signature(
    body: bytes,
    secret: str,
    provided_signature: str,
    algorithm: str = "sha256",
) -> bool:
    """Verify an HMAC signature against the request body."""
    expected = compute_hmac_signature(secret, body, algorithm)
    return hmac.compare_digest(expected, provided_signature)


def extract_signature(headers: dict, header_name: str = "X-Hub-Signature-256") -> Optional[str]:
    """Extract signature from request headers (case-insensitive lookup)."""
    for key, value in headers.items():
        if key.lower() == header_name.lower():
            return value
    return None


def authenticate_request(
    body: bytes,
    headers: dict,
    secret: Optional[str],
    signature_header: str = "X-Hub-Signature-256",
    algorithm: str = "sha256",
) -> tuple[bool, str]:
    """Authenticate an incoming webhook request.

    Returns a (success, reason) tuple.
    """
    if not secret:
        return True, "no secret configured, skipping auth"

    signature = extract_signature(headers, signature_header)
    if not signature:
        logger.warning("Missing signature header: %s", signature_header)
        return False, f"missing header {signature_header}"

    if not verify_signature(body, secret, signature, algorithm):
        logger.warning("Signature mismatch for header %s", signature_header)
        return False, "signature mismatch"

    return True, "ok"
