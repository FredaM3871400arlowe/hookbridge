"""Relay module: forwards transformed payloads to target URLs."""

import logging
import httpx
from typing import Any

logger = logging.getLogger(__name__)

DEFAULT_TIMEOUT = 10.0
DEFAULT_HEADERS = {"Content-Type": "application/json"}


class RelayError(Exception):
    """Raised when a relay attempt fails after retries."""

    def __init__(self, url: str, status_code: int | None = None, message: str = ""):
        self.url = url
        self.status_code = status_code
        self.message = message
        super().__init__(f"Relay to {url!r} failed: {message or status_code}")


def relay_payload(
    target_url: str,
    payload: dict[str, Any],
    headers: dict[str, str] | None = None,
    timeout: float = DEFAULT_TIMEOUT,
    retries: int = 2,
) -> httpx.Response:
    """POST *payload* as JSON to *target_url*.

    Retries up to *retries* times on network errors or 5xx responses.
    Raises :class:`RelayError` when all attempts are exhausted.
    """
    merged_headers = {**DEFAULT_HEADERS, **(headers or {})}
    last_exc: Exception | None = None

    for attempt in range(1, retries + 2):  # +2 → initial attempt + retries
        try:
            response = httpx.post(
                target_url,
                json=payload,
                headers=merged_headers,
                timeout=timeout,
                follow_redirects=True,
            )
            if response.is_success:
                logger.info(
                    "Relayed to %s — status %s (attempt %d)",
                    target_url,
                    response.status_code,
                    attempt,
                )
                return response

            logger.warning(
                "Non-success response %s from %s (attempt %d)",
                response.status_code,
                target_url,
                attempt,
            )
            last_exc = RelayError(target_url, status_code=response.status_code)

        except httpx.RequestError as exc:
            logger.warning(
                "Request error relaying to %s (attempt %d): %s",
                target_url,
                attempt,
                exc,
            )
            last_exc = exc

    raise RelayError(
        target_url,
        message=str(last_exc),
    ) from last_exc
