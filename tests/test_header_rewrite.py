"""Tests for hookbridge.header_rewrite."""

import pytest

from hookbridge.header_rewrite import (
    HeaderRewriteConfig,
    apply_header_rewrites,
    config_from_dict,
    get_route_rewrite_config,
)


# ---------------------------------------------------------------------------
# config_from_dict
# ---------------------------------------------------------------------------

def test_config_from_dict_defaults():
    cfg = config_from_dict({})
    assert cfg.add == {}
    assert cfg.set == {}
    assert cfg.remove == []


def test_config_from_dict_full():
    cfg = config_from_dict({
        "add": {"X-Source": "hookbridge"},
        "set": {"Content-Type": "application/json"},
        "remove": ["Authorization", "Cookie"],
    })
    assert cfg.add == {"X-Source": "hookbridge"}
    assert cfg.set == {"Content-Type": "application/json"}
    assert cfg.remove == ["authorization", "cookie"]


def test_config_remove_lowercased():
    cfg = config_from_dict({"remove": ["X-SECRET", "X-Token"]})
    assert "x-secret" in cfg.remove
    assert "x-token" in cfg.remove


# ---------------------------------------------------------------------------
# get_route_rewrite_config
# ---------------------------------------------------------------------------

class _FakeRoute:
    def __init__(self, header_rewrite=None):
        self.header_rewrite = header_rewrite


def test_get_route_rewrite_config_none_when_missing():
    assert get_route_rewrite_config(_FakeRoute()) is None


def test_get_route_rewrite_config_passthrough_instance():
    cfg = HeaderRewriteConfig(add={"X-A": "1"})
    result = get_route_rewrite_config(_FakeRoute(header_rewrite=cfg))
    assert result is cfg


def test_get_route_rewrite_config_parses_dict():
    route = _FakeRoute(header_rewrite={"set": {"X-Env": "prod"}})
    result = get_route_rewrite_config(route)
    assert result is not None
    assert result.set == {"X-Env": "prod"}


# ---------------------------------------------------------------------------
# apply_header_rewrites
# ---------------------------------------------------------------------------

def test_remove_strips_header():
    cfg = HeaderRewriteConfig(remove=["x-secret"])
    result = apply_header_rewrites({"X-Secret": "abc", "Content-Type": "text/plain"}, cfg)
    assert "X-Secret" not in result
    assert "Content-Type" in result


def test_add_does_not_overwrite_existing():
    cfg = HeaderRewriteConfig(add={"X-Source": "new"})
    result = apply_header_rewrites({"X-Source": "original"}, cfg)
    assert result["X-Source"] == "original"


def test_add_inserts_missing_header():
    cfg = HeaderRewriteConfig(add={"X-Source": "hookbridge"})
    result = apply_header_rewrites({}, cfg)
    assert result["X-Source"] == "hookbridge"


def test_set_overwrites_existing():
    cfg = HeaderRewriteConfig(set={"Content-Type": "application/json"})
    result = apply_header_rewrites({"Content-Type": "text/plain"}, cfg)
    assert result["Content-Type"] == "application/json"


def test_set_adds_when_absent():
    cfg = HeaderRewriteConfig(set={"X-New": "yes"})
    result = apply_header_rewrites({}, cfg)
    assert result["X-New"] == "yes"


def test_remove_before_add():
    """Remove runs before add, so a removed header can be re-added."""
    cfg = HeaderRewriteConfig(
        remove=["x-token"],
        add={"X-Token": "fresh"},
    )
    result = apply_header_rewrites({"X-Token": "stale"}, cfg)
    assert result["X-Token"] == "fresh"


def test_combined_operations():
    headers = {
        "Authorization": "Bearer secret",
        "X-Request-ID": "abc123",
        "Content-Type": "text/plain",
    }
    cfg = HeaderRewriteConfig(
        remove=["authorization"],
        add={"X-Source": "hookbridge"},
        set={"Content-Type": "application/json"},
    )
    result = apply_header_rewrites(headers, cfg)
    assert "Authorization" not in result
    assert result["X-Source"] == "hookbridge"
    assert result["Content-Type"] == "application/json"
    assert result["X-Request-ID"] == "abc123"
