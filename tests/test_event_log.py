"""Tests for hookbridge.event_log."""

import pytest
from hookbridge.event_log import EventLog, EventEntry


@pytest.fixture
def log():
    return EventLog(max_size=10)


def test_record_returns_entry(log):
    entry = log.record(
        route_id="github",
        status="success",
        target_url="http://example.com/hook",
        status_code=200,
    )
    assert isinstance(entry, EventEntry)
    assert entry.route_id == "github"
    assert entry.status == "success"
    assert entry.status_code == 200
    assert entry.error is None


def test_event_id_increments(log):
    e1 = log.record("r1", "success", "http://a.com", 200)
    e2 = log.record("r1", "failure", "http://a.com", 500)
    assert e1.event_id != e2.event_id
    assert e1.event_id < e2.event_id  # lexicographic order holds for zero-padded


def test_all_returns_all_entries(log):
    log.record("r1", "success", "http://a.com", 200)
    log.record("r2", "failure", "http://b.com", 500)
    entries = log.all()
    assert len(entries) == 2


def test_for_route_filters_by_route(log):
    log.record("r1", "success", "http://a.com", 200)
    log.record("r2", "failure", "http://b.com", 500)
    log.record("r1", "filtered", "http://a.com")
    r1_entries = log.for_route("r1")
    assert len(r1_entries) == 2
    assert all(e.route_id == "r1" for e in r1_entries)


def test_max_size_evicts_oldest(log):
    for i in range(12):
        log.record("r1", "success", f"http://example.com/{i}", 200)
    assert log.size() == 10  # maxlen=10


def test_clear_empties_log(log):
    log.record("r1", "success", "http://a.com", 200)
    log.clear()
    assert log.size() == 0
    assert log.all() == []


def test_to_dict_contains_all_fields(log):
    entry = log.record(
        route_id="stripe",
        status="failure",
        target_url="http://example.com/stripe",
        status_code=503,
        error="Service unavailable",
        payload_preview='{"event": "charge.created"}',
    )
    d = entry.to_dict()
    assert d["route_id"] == "stripe"
    assert d["status"] == "failure"
    assert d["status_code"] == 503
    assert d["error"] == "Service unavailable"
    assert d["payload_preview"] == '{"event": "charge.created"}'
    assert "timestamp" in d
    assert "event_id" in d


def test_timestamp_is_iso_format(log):
    entry = log.record("r1", "success", "http://a.com", 200)
    # Should not raise
    from datetime import datetime
    dt = datetime.fromisoformat(entry.timestamp)
    assert dt is not None
