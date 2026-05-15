"""Tests for hookbridge/event_log.py"""

import pytest
from hookbridge.event_log import EventLog, EventEntry


@pytest.fixture
def log():
    return EventLog(max_size=5)


def test_record_returns_entry(log):
    entry = log.record("github", "success", "http://example.com", http_status=200)
    assert isinstance(entry, EventEntry)
    assert entry.route == "github"
    assert entry.status == "success"
    assert entry.http_status == 200
    assert entry.error is None


def test_event_id_increments(log):
    e1 = log.record("r", "success", "http://a.com")
    e2 = log.record("r", "failure", "http://b.com")
    assert e2.event_id == e1.event_id + 1


def test_all_returns_all_entries(log):
    log.record("r1", "success", "http://a.com")
    log.record("r2", "success", "http://b.com")
    assert len(log.all()) == 2


def test_for_route_filters_by_route(log):
    log.record("alpha", "success", "http://a.com")
    log.record("beta", "failure", "http://b.com")
    log.record("alpha", "filtered", "http://c.com")
    result = log.for_route("alpha")
    assert len(result) == 2
    assert all(e.route == "alpha" for e in result)


def test_get_by_id(log):
    e = log.record("r", "success", "http://x.com")
    found = log.get(e.event_id)
    assert found is not None
    assert found.event_id == e.event_id


def test_get_missing_returns_none(log):
    assert log.get(9999) is None


def test_max_size_evicts_oldest(log):
    for i in range(6):
        log.record("r", "success", f"http://url{i}.com")
    assert log.size() == 5


def test_clear_resets(log):
    log.record("r", "success", "http://a.com")
    log.clear()
    assert log.size() == 0
    e = log.record("r", "success", "http://b.com")
    assert e.event_id == 1


def test_to_dict_contains_expected_keys(log):
    e = log.record("r", "failure", "http://fail.com", error="timeout")
    d = e.to_dict()
    for key in ("event_id", "route", "status", "target_url", "http_status", "error", "timestamp"):
        assert key in d
    assert d["error"] == "timeout"
