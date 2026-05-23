"""Tests for hookbridge.request_throttle."""

from __future__ import annotations

import threading
import pytest

from hookbridge.request_throttle import (
    ThrottleConfig,
    ThrottleState,
    check_throttle_for_route,
    release_throttle,
    get_state,
    _states,
    _global_lock,
)


@pytest.fixture(autouse=True)
def clear_states():
    with _global_lock:
        _states.clear()
    yield
    with _global_lock:
        _states.clear()


def test_default_max_concurrent():
    cfg = ThrottleConfig()
    assert cfg.max_concurrent == 10


def test_custom_max_concurrent():
    cfg = ThrottleConfig(max_concurrent=5)
    assert cfg.max_concurrent == 5


def test_max_concurrent_below_minimum_raises():
    with pytest.raises(ValueError, match="at least 1"):
        ThrottleConfig(max_concurrent=0)


def test_max_concurrent_above_maximum_raises():
    with pytest.raises(ValueError, match="1000"):
        ThrottleConfig(max_concurrent=1001)


def test_acquire_within_limit():
    state = ThrottleState(config=ThrottleConfig(max_concurrent=2))
    assert state.acquire() is True
    assert state.active == 1


def test_acquire_at_capacity_returns_false():
    state = ThrottleState(config=ThrottleConfig(max_concurrent=2))
    state.acquire()
    state.acquire()
    assert state.acquire() is False
    assert state.active == 2


def test_release_decrements_active():
    state = ThrottleState(config=ThrottleConfig(max_concurrent=2))
    state.acquire()
    state.release()
    assert state.active == 0


def test_release_does_not_go_below_zero():
    state = ThrottleState(config=ThrottleConfig(max_concurrent=2))
    state.release()  # release without prior acquire
    assert state.active == 0


def test_to_dict_reflects_state():
    state = ThrottleState(config=ThrottleConfig(max_concurrent=3))
    state.acquire()
    d = state.to_dict()
    assert d["max_concurrent"] == 3
    assert d["active"] == 1
    assert d["available"] == 2


def test_check_throttle_no_config_returns_none():
    class Route:
        throttle = None

    result = check_throttle_for_route("r1", Route())
    assert result is None


def test_check_throttle_allows_within_limit():
    class Route:
        throttle = {"max_concurrent": 3}

    result = check_throttle_for_route("r2", Route())
    assert result is None
    assert _states["r2"].active == 1


def test_check_throttle_blocks_over_limit():
    class Route:
        throttle = {"max_concurrent": 1}

    check_throttle_for_route("r3", Route())
    result = check_throttle_for_route("r3", Route())
    assert result is not None
    assert result["status"] == 429
    assert "r3" in result["detail"]


def test_release_throttle_decrements():
    class Route:
        throttle = {"max_concurrent": 2}

    check_throttle_for_route("r4", Route())
    assert _states["r4"].active == 1
    release_throttle("r4")
    assert _states["r4"].active == 0


def test_release_throttle_unknown_route_is_noop():
    release_throttle("nonexistent_route")  # should not raise


def test_concurrent_acquire_respects_limit():
    cfg = ThrottleConfig(max_concurrent=5)
    state = ThrottleState(config=cfg)
    results = []
    barrier = threading.Barrier(10)

    def try_acquire():
        barrier.wait()
        results.append(state.acquire())

    threads = [threading.Thread(target=try_acquire) for _ in range(10)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert results.count(True) == 5
    assert results.count(False) == 5
