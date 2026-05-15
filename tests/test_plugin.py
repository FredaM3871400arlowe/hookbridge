"""Tests for hookbridge.plugin and hookbridge.plugin_middleware."""

import pytest

from hookbridge import plugin as plug
from hookbridge.plugin_middleware import (
    get_route_plugins,
    run_plugins_for_route,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _add_flag(payload: dict, route_name: str) -> dict:
    return {**payload, "flagged": True}


def _append_route(payload: dict, route_name: str) -> dict:
    return {**payload, "route": route_name}


@pytest.fixture(autouse=True)
def clean_registry():
    """Ensure each test starts with a clean plugin registry."""
    original = dict(plug._REGISTRY)
    plug._REGISTRY.clear()
    yield
    plug._REGISTRY.clear()
    plug._REGISTRY.update(original)


# ---------------------------------------------------------------------------
# plugin.py
# ---------------------------------------------------------------------------

def test_register_and_list():
    plug.register_plugin("add_flag", _add_flag)
    assert "add_flag" in plug.list_plugins()


def test_unregister_removes_plugin():
    plug.register_plugin("add_flag", _add_flag)
    plug.unregister_plugin("add_flag")
    assert "add_flag" not in plug.list_plugins()


def test_apply_plugins_single():
    plug.register_plugin("add_flag", _add_flag)
    result = plug.apply_plugins({"x": 1}, "my_route", ["add_flag"])
    assert result == {"x": 1, "flagged": True}


def test_apply_plugins_chained():
    plug.register_plugin("add_flag", _add_flag)
    plug.register_plugin("append_route", _append_route)
    result = plug.apply_plugins({"x": 1}, "r1", ["add_flag", "append_route"])
    assert result["flagged"] is True
    assert result["route"] == "r1"


def test_apply_plugins_no_names_returns_original():
    payload = {"a": 1}
    assert plug.apply_plugins(payload, "r", []) is payload
    assert plug.apply_plugins(payload, "r", None) is payload


def test_apply_plugins_unknown_raises():
    with pytest.raises(KeyError, match="not_registered"):
        plug.apply_plugins({}, "r", ["not_registered"])


def test_load_plugin_from_dotpath_bad_module():
    with pytest.raises(ImportError):
        plug.load_plugin_from_dotpath("nonexistent.module.xyz")


# ---------------------------------------------------------------------------
# plugin_middleware.py
# ---------------------------------------------------------------------------

def test_get_route_plugins_from_dict():
    route = {"name": "r", "plugins": ["p1", "p2"]}
    assert get_route_plugins(route) == ["p1", "p2"]


def test_get_route_plugins_missing_returns_empty():
    assert get_route_plugins({"name": "r"}) == []


def test_get_route_plugins_from_object():
    class FakeRoute:
        name = "r"
        plugins = ["p1"]

    assert get_route_plugins(FakeRoute()) == ["p1"]


def test_run_plugins_for_route_applies_plugin():
    plug.register_plugin("add_flag", _add_flag)
    route = {"name": "test_route", "plugins": ["add_flag"]}
    result = run_plugins_for_route({"val": 42}, route)
    assert result["flagged"] is True


def test_run_plugins_for_route_no_plugins_unchanged():
    payload = {"val": 1}
    result = run_plugins_for_route(payload, {"name": "r"})
    assert result is payload
