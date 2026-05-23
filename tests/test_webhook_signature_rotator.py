"""Tests for hookbridge.webhook_signature_rotator."""

import time
import pytest

from hookbridge.webhook_signature_rotator import (
    SecretRotator,
    RotationEntry,
    get_rotator,
    reset_rotators,
)
from hookbridge.auth import compute_hmac_signature


@pytest.fixture(autouse=True)
def clean_rotators():
    reset_rotators()
    yield
    reset_rotators()


def _make_sig_header(payload: bytes, secret: str, alg: str = "sha256") -> str:
    sig = compute_hmac_signature(payload, secret, alg)
    return f"{alg}={sig}"


def test_add_single_secret():
    r = SecretRotator()
    r.add_secret("mysecret")
    assert r.primary_secret() == "mysecret"
    assert len(r) == 1


def test_primary_is_most_recent():
    r = SecretRotator()
    r.add_secret("old")
    r.add_secret("new")
    assert r.primary_secret() == "new"


def test_all_active_secrets_returned():
    r = SecretRotator()
    r.add_secret("s1")
    r.add_secret("s2")
    assert set(r.all_active_secrets()) == {"s1", "s2"}


def test_expired_secret_is_purged():
    r = SecretRotator()
    r.add_secret("old", ttl_seconds=-1)  # already expired
    r.add_secret("new")
    assert "old" not in r.all_active_secrets()
    assert len(r) == 1


def test_verify_any_with_primary_secret():
    r = SecretRotator()
    r.add_secret("primary")
    payload = b'{"event": "push"}'
    header = _make_sig_header(payload, "primary")
    assert r.verify_any(payload, header) is True


def test_verify_any_with_old_secret_still_valid():
    r = SecretRotator()
    r.add_secret("old")
    r.add_secret("new")
    payload = b'{"event": "push"}'
    old_header = _make_sig_header(payload, "old")
    assert r.verify_any(payload, old_header) is True


def test_verify_any_wrong_secret_fails():
    r = SecretRotator()
    r.add_secret("correct")
    payload = b'{"event": "push"}'
    bad_header = _make_sig_header(payload, "wrong")
    assert r.verify_any(payload, bad_header) is False


def test_verify_any_missing_signature_fails():
    r = SecretRotator()
    r.add_secret("secret")
    assert r.verify_any(b"data", "") is False


def test_get_rotator_returns_same_instance():
    r1 = get_rotator("route-a")
    r2 = get_rotator("route-a")
    assert r1 is r2


def test_get_rotator_different_routes_are_isolated():
    get_rotator("route-x").add_secret("sx")
    get_rotator("route-y").add_secret("sy")
    assert get_rotator("route-x").primary_secret() == "sx"
    assert get_rotator("route-y").primary_secret() == "sy"


def test_empty_rotator_primary_is_none():
    r = SecretRotator()
    assert r.primary_secret() is None
