"""Tests for CORS config, header building, and middleware helpers."""

import pytest
from hookbridge.cors import (
    CORSConfig,
    config_from_dict,
    build_cors_headers,
    is_preflight,
    get_cors_config,
)
from hookbridge.cors_middleware import apply_cors_to_handler, flush_cors_headers


# ---------------------------------------------------------------------------
# config_from_dict
# ---------------------------------------------------------------------------

def test_config_from_dict_defaults():
    cfg = config_from_dict({})
    assert cfg.allowed_origins == ["*"]
    assert "POST" in cfg.allowed_methods
    assert cfg.allow_credentials is False
    assert cfg.max_age_seconds == 600


def test_config_from_dict_custom():
    cfg = config_from_dict({
        "allowed_origins": ["https://example.com"],
        "allow_credentials": True,
        "max_age_seconds": 3600,
    })
    assert cfg.allowed_origins == ["https://example.com"]
    assert cfg.allow_credentials is True
    assert cfg.max_age_seconds == 3600


# ---------------------------------------------------------------------------
# build_cors_headers
# ---------------------------------------------------------------------------

def test_wildcard_origin_always_set():
    cfg = CORSConfig(allowed_origins=["*"])
    headers = build_cors_headers(cfg, "https://any.example.com")
    assert headers["Access-Control-Allow-Origin"] == "*"


def test_specific_origin_match():
    cfg = CORSConfig(allowed_origins=["https://trusted.example.com"])
    headers = build_cors_headers(cfg, "https://trusted.example.com")
    assert headers["Access-Control-Allow-Origin"] == "https://trusted.example.com"


def test_specific_origin_no_match_omits_header():
    cfg = CORSConfig(allowed_origins=["https://trusted.example.com"])
    headers = build_cors_headers(cfg, "https://evil.example.com")
    assert "Access-Control-Allow-Origin" not in headers


def test_credentials_header_included_when_true():
    cfg = CORSConfig(allow_credentials=True)
    headers = build_cors_headers(cfg)
    assert headers.get("Access-Control-Allow-Credentials") == "true"


def test_credentials_header_absent_when_false():
    cfg = CORSConfig(allow_credentials=False)
    headers = build_cors_headers(cfg)
    assert "Access-Control-Allow-Credentials" not in headers


def test_max_age_in_headers():
    cfg = CORSConfig(max_age_seconds=1200)
    headers = build_cors_headers(cfg)
    assert headers["Access-Control-Max-Age"] == "1200"


# ---------------------------------------------------------------------------
# is_preflight
# ---------------------------------------------------------------------------

def test_is_preflight_true():
    assert is_preflight("OPTIONS", {"Origin": "https://example.com"}) is True


def test_is_preflight_false_wrong_method():
    assert is_preflight("POST", {"Origin": "https://example.com"}) is False


def test_is_preflight_false_no_origin():
    assert is_preflight("OPTIONS", {"Content-Type": "application/json"}) is False


# ---------------------------------------------------------------------------
# get_cors_config
# ---------------------------------------------------------------------------

def test_get_cors_config_none_when_missing():
    class FakeConfig:
        pass
    assert get_cors_config(FakeConfig()) is None


def test_get_cors_config_from_dict_attr():
    class FakeConfig:
        cors = {"allowed_origins": ["https://a.example.com"], "max_age_seconds": 300}
    result = get_cors_config(FakeConfig())
    assert isinstance(result, CORSConfig)
    assert result.max_age_seconds == 300


def test_get_cors_config_passthrough_when_already_config():
    class FakeConfig:
        cors = CORSConfig(max_age_seconds=999)
    result = get_cors_config(FakeConfig())
    assert result.max_age_seconds == 999
