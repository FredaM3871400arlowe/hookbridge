"""Tests for hookbridge.response_cache."""

import time
import pytest

from hookbridge.response_cache import (
    CacheConfig,
    CacheEntry,
    ResponseCache,
    config_from_dict,
)


# ---------------------------------------------------------------------------
# CacheConfig validation
# ---------------------------------------------------------------------------

def test_default_config_values():
    cfg = CacheConfig()
    assert cfg.ttl_seconds == 300.0
    assert cfg.max_entries == 1000


def test_ttl_zero_raises():
    with pytest.raises(ValueError, match="ttl_seconds"):
        CacheConfig(ttl_seconds=0)


def test_ttl_negative_raises():
    with pytest.raises(ValueError):
        CacheConfig(ttl_seconds=-1)


def test_max_entries_zero_raises():
    with pytest.raises(ValueError, match="max_entries"):
        CacheConfig(max_entries=0)


def test_max_entries_too_large_raises():
    with pytest.raises(ValueError):
        CacheConfig(max_entries=200_000)


# ---------------------------------------------------------------------------
# CacheEntry
# ---------------------------------------------------------------------------

def test_entry_not_expired_immediately():
    entry = CacheEntry("rid", "route1", 200, b'{"ok":true}')
    assert not entry.is_expired(300.0)


def test_entry_expired_after_ttl(monkeypatch):
    entry = CacheEntry("rid", "route1", 200, b"{}")
    monkeypatch.setattr("hookbridge.response_cache.time.monotonic",
                        lambda: entry.created_at + 400)
    assert entry.is_expired(300.0)


def test_entry_to_dict_keys():
    entry = CacheEntry("abc", "r1", 202, b"data")
    d = entry.to_dict()
    assert d["request_id"] == "abc"
    assert d["route_id"] == "r1"
    assert d["status_code"] == 202
    assert "age_seconds" in d


# ---------------------------------------------------------------------------
# ResponseCache
# ---------------------------------------------------------------------------

@pytest.fixture
def cache():
    return ResponseCache(CacheConfig(ttl_seconds=60.0, max_entries=5))


def _entry(request_id="r1", route_id="route-a", status=200):
    return CacheEntry(request_id, route_id, status, b"{}")


def test_put_and_get(cache):
    e = _entry()
    cache.put(e)
    result = cache.get("r1", "route-a")
    assert result is not None
    assert result.status_code == 200


def test_get_missing_returns_none(cache):
    assert cache.get("nonexistent", "route-a") is None


def test_get_expired_returns_none(cache, monkeypatch):
    e = _entry()
    cache.put(e)
    monkeypatch.setattr("hookbridge.response_cache.time.monotonic",
                        lambda: e.created_at + 120)
    assert cache.get("r1", "route-a") is None


def test_size_tracks_entries(cache):
    cache.put(_entry("r1"))
    cache.put(_entry("r2"))
    assert cache.size() == 2


def test_max_entries_evicts_oldest(cache):
    for i in range(6):
        cache.put(_entry(request_id=f"r{i}"))
    assert cache.size() <= 5


def test_clear_empties_cache(cache):
    cache.put(_entry())
    cache.clear()
    assert cache.size() == 0


def test_different_routes_do_not_collide(cache):
    cache.put(CacheEntry("same-id", "route-a", 200, b"a"))
    cache.put(CacheEntry("same-id", "route-b", 201, b"b"))
    assert cache.get("same-id", "route-a").status_code == 200
    assert cache.get("same-id", "route-b").status_code == 201


# ---------------------------------------------------------------------------
# config_from_dict
# ---------------------------------------------------------------------------

def test_config_from_dict_custom():
    cfg = config_from_dict({"ttl_seconds": 120, "max_entries": 50})
    assert cfg.ttl_seconds == 120.0
    assert cfg.max_entries == 50


def test_config_from_dict_defaults():
    cfg = config_from_dict({})
    assert cfg.ttl_seconds == 300.0
    assert cfg.max_entries == 1000
