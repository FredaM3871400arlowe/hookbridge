"""Tests for hookbridge.payload_validator and .payload_validator_middleware."""

import pytest

from hookbridge.payload_validator import (
    ValidationError,
    validate_payload,
    get_route_schema,
    check_payload_for_route,
    build_validation_response,
)
from hookbridge.payload_validator_middleware import (
    run_validation_for_route,
    validation_response_to_bytes,
)


SCHEMA = {
    "type": "object",
    "required": ["event", "data"],
    "properties": {
        "event": {"type": "string"},
        "data": {"type": "object"},
    },
    "additionalProperties": False,
}


def test_validate_payload_valid():
    err = validate_payload({"event": "push", "data": {}}, SCHEMA)
    assert err is None


def test_validate_payload_missing_required():
    err = validate_payload({"event": "push"}, SCHEMA)
    assert isinstance(err, ValidationError)
    assert "data" in str(err)


def test_validate_payload_wrong_type():
    err = validate_payload({"event": 42, "data": {}}, SCHEMA)
    assert isinstance(err, ValidationError)


def test_validate_payload_additional_property():
    err = validate_payload({"event": "push", "data": {}, "extra": True}, SCHEMA)
    assert isinstance(err, ValidationError)


def test_validate_payload_path_populated():
    err = validate_payload({"event": 99, "data": {}}, SCHEMA)
    assert err is not None
    assert err.path == "event"


def test_get_route_schema_present():
    cfg = {"path": "/hook", "payload_schema": SCHEMA}
    assert get_route_schema(cfg) is SCHEMA


def test_get_route_schema_absent():
    cfg = {"path": "/hook"}
    assert get_route_schema(cfg) is None


def test_check_payload_for_route_no_schema():
    assert check_payload_for_route({"anything": True}, {"path": "/hook"}) is None


def test_check_payload_for_route_valid():
    cfg = {"path": "/hook", "payload_schema": SCHEMA}
    assert check_payload_for_route({"event": "ping", "data": {}}, cfg) is None


def test_check_payload_for_route_invalid():
    cfg = {"path": "/hook", "payload_schema": SCHEMA}
    err = check_payload_for_route({"event": "ping"}, cfg)
    assert isinstance(err, ValidationError)


def test_build_validation_response_includes_path():
    err = ValidationError("bad field", path="data/id")
    resp = build_validation_response(err)
    assert resp["error"] == "payload_validation_failed"
    assert resp["path"] == "data/id"


def test_build_validation_response_no_path():
    err = ValidationError("bad field")
    resp = build_validation_response(err)
    assert "path" not in resp


def test_run_validation_for_route_success():
    cfg = {"path": "/hook", "payload_schema": SCHEMA}
    result = run_validation_for_route({"event": "x", "data": {}}, cfg, "/hook")
    assert result is None


def test_run_validation_for_route_failure():
    cfg = {"path": "/hook", "payload_schema": SCHEMA}
    result = run_validation_for_route({"event": "x"}, cfg, "/hook")
    assert result is not None
    assert result["status"] == 422
    assert result["body"]["route"] == "/hook"


def test_run_validation_no_schema():
    result = run_validation_for_route({"whatever": 1}, {"path": "/hook"}, "/hook")
    assert result is None


def test_validation_response_to_bytes():
    response = {"status": 422, "body": {"error": "payload_validation_failed", "detail": "oops"}}
    raw = validation_response_to_bytes(response)
    assert isinstance(raw, bytes)
    assert b"payload_validation_failed" in raw
