"""Tests for hookbridge.auth module."""

import hashlib
import hmac

import pytest

from hookbridge.auth import (
    authenticate_request,
    compute_hmac_signature,
    extract_signature,
    verify_signature,
)

SECRET = "test-secret"
BODY = b'{"event": "push"}'


def _make_sig(secret: str, body: bytes, alg: str = "sha256") -> str:
    mac = hmac.new(secret.encode(), body, getattr(hashlib, alg))
    return f"{alg}={mac.hexdigest()}"


def test_compute_hmac_signature_matches_manual():
    result = compute_hmac_signature(SECRET, BODY)
    assert result == _make_sig(SECRET, BODY)


def test_compute_hmac_signature_sha1():
    result = compute_hmac_signature(SECRET, BODY, algorithm="sha1")
    assert result.startswith("sha1=")


def test_verify_signature_valid():
    sig = compute_hmac_signature(SECRET, BODY)
    assert verify_signature(BODY, SECRET, sig) is True


def test_verify_signature_invalid():
    assert verify_signature(BODY, SECRET, "sha256=badhash") is False


def test_verify_signature_wrong_body():
    sig = compute_hmac_signature(SECRET, BODY)
    assert verify_signature(b"other body", SECRET, sig) is False


def test_extract_signature_found():
    headers = {"X-Hub-Signature-256": "sha256=abc123"}
    assert extract_signature(headers) == "sha256=abc123"


def test_extract_signature_case_insensitive():
    headers = {"x-hub-signature-256": "sha256=abc123"}
    assert extract_signature(headers) == "sha256=abc123"


def test_extract_signature_missing():
    assert extract_signature({}) is None


def test_authenticate_request_no_secret():
    ok, reason = authenticate_request(BODY, {}, secret=None)
    assert ok is True
    assert "no secret" in reason


def test_authenticate_request_valid():
    sig = compute_hmac_signature(SECRET, BODY)
    headers = {"X-Hub-Signature-256": sig}
    ok, reason = authenticate_request(BODY, headers, secret=SECRET)
    assert ok is True
    assert reason == "ok"


def test_authenticate_request_missing_header():
    ok, reason = authenticate_request(BODY, {}, secret=SECRET)
    assert ok is False
    assert "missing header" in reason


def test_authenticate_request_bad_signature():
    headers = {"X-Hub-Signature-256": "sha256=badhash"}
    ok, reason = authenticate_request(BODY, headers, secret=SECRET)
    assert ok is False
    assert "mismatch" in reason


def test_authenticate_request_custom_header():
    sig = compute_hmac_signature(SECRET, BODY)
    headers = {"X-Webhook-Signature": sig}
    ok, reason = authenticate_request(
        BODY, headers, secret=SECRET, signature_header="X-Webhook-Signature"
    )
    assert ok is True
