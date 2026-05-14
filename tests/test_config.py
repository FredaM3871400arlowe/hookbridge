"""Tests for hookbridge configuration loading."""

import json
import os
import pytest
from hookbridge.config import load_config, AppConfig, RouteConfig


@pytest.fixture
def config_file(tmp_path):
    """Write a temporary config file and return its path."""
    data = {
        "host": "127.0.0.1",
        "port": 9090,
        "log_level": "DEBUG",
        "routes": [
            {
                "name": "test-route",
                "source_path": "/hooks/test",
                "target_url": "https://example.com/hook",
                "secret": "s3cr3t",
                "filter_rules": [
                    {"field": "action", "operator": "eq", "value": "push"}
                ],
                "transform": "my_transform",
            }
        ],
    }
    path = tmp_path / "hookbridge.json"
    path.write_text(json.dumps(data))
    return str(path)


def test_load_config_from_file(config_file):
    cfg = load_config(config_file)
    assert isinstance(cfg, AppConfig)
    assert cfg.host == "127.0.0.1"
    assert cfg.port == 9090
    assert cfg.log_level == "DEBUG"
    assert len(cfg.routes) == 1


def test_route_fields(config_file):
    cfg = load_config(config_file)
    route = cfg.routes[0]
    assert isinstance(route, RouteConfig)
    assert route.name == "test-route"
    assert route.source_path == "/hooks/test"
    assert route.target_url == "https://example.com/hook"
    assert route.secret == "s3cr3t"
    assert route.transform == "my_transform"
    assert route.filter_rules == [{"field": "action", "operator": "eq", "value": "push"}]


def test_load_config_defaults_when_missing(tmp_path):
    nonexistent = str(tmp_path / "missing.json")
    cfg = load_config(nonexistent)
    assert cfg.host == "0.0.0.0"
    assert cfg.port == 8080
    assert cfg.log_level == "INFO"
    assert cfg.routes == []


def test_load_config_from_env(config_file, monkeypatch):
    monkeypatch.setenv("HOOKBRIDGE_CONFIG", config_file)
    cfg = load_config()
    assert cfg.port == 9090
