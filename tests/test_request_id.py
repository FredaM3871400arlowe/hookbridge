"""Tests for hookbridge/request_id.py."""

import pytest
from hookbridge.request_id import (
    generate_request_id,
    extract_request_id,
    resolve_request_id,
    attach_request_id_header,
    build_request_id_context,
    _GENERATED_PREFIX,
    _HEADER_NAME,
)


def test_generate_request_id_has_prefix():
    rid = generate_request_id()
    assert rid.startswith(_GENERATED_PREFIX)


def test_generate_request_id_is_unique():
    ids = {generate_request_id() for _ in range(100)}
    assert len(ids) == 100


def test_extract_request_id_found():
    headers = {"X-Request-ID": "abc-123"}
    assert extract_request_id(headers) == "abc-123"


def test_extract_request_id_case_insensitive():
    headers = {"x-request-id": "lower-case-id"}
    assert extract_request_id(headers) == "lower-case-id"


def test_extract_request_id_missing_returns_none():
    headers = {"Content-Type": "application/json"}
    assert extract_request_id(headers) is None


def test_resolve_request_id_reuses_existing():
    headers = {"X-Request-ID": "existing-id-42"}
    rid, generated = resolve_request_id(headers)
    assert rid == "existing-id-42"
    assert generated is False


def test_resolve_request_id_generates_when_absent():
    headers = {}
    rid, generated = resolve_request_id(headers)
    assert rid.startswith(_GENERATED_PREFIX)
    assert generated is True


def test_attach_request_id_header_appends():
    headers: list = [("Content-Type", "application/json")]
    attach_request_id_header(headers, "req-999")
    assert (_HEADER_NAME, "req-999") in headers
    assert len(headers) == 2


def test_attach_request_id_header_does_not_mutate_other_entries():
    headers: list = [("Authorization", "Bearer token")]
    attach_request_id_header(headers, "req-xyz")
    assert headers[0] == ("Authorization", "Bearer token")


def test_build_request_id_context_with_existing():
    headers = {"X-Request-ID": "ctx-id-1"}
    ctx = build_request_id_context(headers)
    assert ctx["request_id"] == "ctx-id-1"
    assert ctx["generated"] is False
    assert ctx["header_name"] == _HEADER_NAME


def test_build_request_id_context_generates_new():
    ctx = build_request_id_context({})
    assert ctx["request_id"].startswith(_GENERATED_PREFIX)
    assert ctx["generated"] is True
    assert ctx["header_name"] == _HEADER_NAME
