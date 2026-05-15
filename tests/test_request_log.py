"""Tests for hookbridge.request_log."""

import time
import pytest
from hookbridge.request_log import RequestLog, RequestEntry


@pytest.fixture
def log() -> RequestLog:
    return RequestLog(max_size=5)


def _record(log: RequestLog, route: str = "/hook", status: int = 200) -> RequestEntry:
    return log.record(
        route=route,
        method="POST",
        headers={"content-type": "application/json"},
        payload={"event": "push"},
        source_ip="127.0.0.1",
        status_code=status,
    )


def test_record_returns_entry(log):
    entry = _record(log)
    assert isinstance(entry, RequestEntry)
    assert entry.route == "/hook"
    assert entry.method == "POST"
    assert entry.status_code == 200


def test_request_id_increments(log):
    e1 = _record(log)
    e2 = _record(log)
    assert e2.request_id == e1.request_id + 1


def test_all_returns_all_entries(log):
    _record(log)
    _record(log)
    _record(log)
    assert len(log.all()) == 3


def test_for_route_filters(log):
    _record(log, route="/hook/a")
    _record(log, route="/hook/b")
    _record(log, route="/hook/a")
    assert len(log.for_route("/hook/a")) == 2
    assert len(log.for_route("/hook/b")) == 1


def test_get_by_id(log):
    entry = _record(log)
    found = log.get(entry.request_id)
    assert found is entry


def test_get_missing_returns_none(log):
    assert log.get(9999) is None


def test_max_size_evicts_oldest(log):
    for _ in range(6):  # max_size=5
        _record(log)
    assert log.size() == 5
    # oldest entry (id=1) should be gone
    assert log.get(1) is None


def test_clear_empties_log(log):
    _record(log)
    _record(log)
    log.clear()
    assert log.size() == 0


def test_timestamp_is_recent(log):
    before = time.time()
    entry = _record(log)
    after = time.time()
    assert before <= entry.timestamp <= after


def test_to_dict_contains_expected_keys(log):
    entry = _record(log)
    d = entry.to_dict()
    for key in ("request_id", "route", "method", "headers", "payload", "source_ip", "timestamp", "status_code"):
        assert key in d
