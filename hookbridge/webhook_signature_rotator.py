"""Webhook secret rotation support — allows multiple active secrets
during a rotation window so old and new secrets both verify."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import List, Optional

from hookbridge.auth import verify_signature, extract_signature


@dataclass
class RotationEntry:
    secret: str
    added_at: float = field(default_factory=time.time)
    expires_at: Optional[float] = None

    def is_expired(self) -> bool:
        if self.expires_at is None:
            return False
        return time.time() > self.expires_at


class SecretRotator:
    """Holds an ordered list of secrets for a route.
    The first non-expired entry is the *primary* (used for outgoing signing).
    All non-expired entries are tried for verification.
    """

    def __init__(self) -> None:
        self._entries: List[RotationEntry] = []

    def add_secret(self, secret: str, ttl_seconds: Optional[float] = None) -> None:
        """Prepend a new secret.  Optionally expire old ones after *ttl_seconds*."""
        expires_at = time.time() + ttl_seconds if ttl_seconds is not None else None
        self._entries.insert(0, RotationEntry(secret=secret, expires_at=expires_at))
        self._purge_expired()

    def primary_secret(self) -> Optional[str]:
        self._purge_expired()
        return self._entries[0].secret if self._entries else None

    def all_active_secrets(self) -> List[str]:
        self._purge_expired()
        return [e.secret for e in self._entries]

    def verify_any(self, payload: bytes, signature_header: str, algorithm: str = "sha256") -> bool:
        """Return True if *signature_header* is valid under any active secret."""
        sig = extract_signature(signature_header)
        if sig is None:
            return False
        for secret in self.all_active_secrets():
            if verify_signature(payload, sig, secret, algorithm):
                return True
        return False

    def _purge_expired(self) -> None:
        self._entries = [e for e in self._entries if not e.is_expired()]

    def __len__(self) -> int:
        return len(self._entries)


# Global per-route registry
_rotators: dict[str, SecretRotator] = {}


def get_rotator(route_id: str) -> SecretRotator:
    if route_id not in _rotators:
        _rotators[route_id] = SecretRotator()
    return _rotators[route_id]


def reset_rotators() -> None:
    """Clear all rotators — useful in tests."""
    _rotators.clear()
