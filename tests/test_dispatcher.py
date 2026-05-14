"""Tests for hookbridge.dispatcher and hookbridge.relay."""

import pytest
import httpx
import respx

from hookbridge.config import RouteConfig
from hookbridge.dispatcher import dispatch, dispatch_all, DispatchResult
from hookbridge.relay import relay_payload, RelayError


TARGET = "https://example.com/hook"


def make_route(**kwargs) -> RouteConfig:
    defaults = {
        "name": "test-route",
        "source": "/incoming",
        "target": TARGET,
        "filters": None,
        "transform": None,
        "headers": None,
        "retries": 0,
    }
    defaults.update(kwargs)
    return RouteConfig(**defaults)


# ---------------------------------------------------------------------------
# relay_payload tests
# ---------------------------------------------------------------------------

@respx.mock
def test_relay_success():
    respx.post(TARGET).mock(return_value=httpx.Response(200))
    response = relay_payload(TARGET, {"event": "push"}, retries=0)
    assert response.status_code == 200


@respx.mock
def test_relay_raises_on_server_error():
    respx.post(TARGET).mock(return_value=httpx.Response(500))
    with pytest.raises(RelayError) as exc_info:
        relay_payload(TARGET, {"event": "push"}, retries=0)
    assert exc_info.value.status_code == 500


@respx.mock
def test_relay_retries_then_raises():
    # Always return 503
    respx.post(TARGET).mock(return_value=httpx.Response(503))
    with pytest.raises(RelayError):
        relay_payload(TARGET, {}, retries=2)
    # Called initial + 2 retries = 3 times
    assert respx.calls.call_count == 3


@respx.mock
def test_relay_network_error_raises():
    respx.post(TARGET).mock(side_effect=httpx.ConnectError("refused"))
    with pytest.raises(RelayError):
        relay_payload(TARGET, {}, retries=0)


# ---------------------------------------------------------------------------
# dispatch tests
# ---------------------------------------------------------------------------

@respx.mock
def test_dispatch_success():
    respx.post(TARGET).mock(return_value=httpx.Response(200))
    route = make_route()
    result = dispatch(route, {"action": "opened"})
    assert result.success is True
    assert result.skipped is False
    assert result.status_code == 200


@respx.mock
def test_dispatch_skipped_by_filter():
    route = make_route(filters=[{"field": "action", "op": "eq", "value": "closed"}])
    result = dispatch(route, {"action": "opened"})
    assert result.skipped is True
    assert result.success is False
    # No HTTP call should have been made
    assert len(respx.calls) == 0


@respx.mock
def test_dispatch_filter_passes_and_relays():
    respx.post(TARGET).mock(return_value=httpx.Response(201))
    route = make_route(filters=[{"field": "action", "op": "eq", "value": "opened"}])
    result = dispatch(route, {"action": "opened"})
    assert result.success is True
    assert result.status_code == 201


@respx.mock
def test_dispatch_relay_failure_returns_error_result():
    respx.post(TARGET).mock(return_value=httpx.Response(500))
    route = make_route(retries=0)
    result = dispatch(route, {"x": 1})
    assert result.success is False
    assert result.error is not None


@respx.mock
def test_dispatch_all_returns_results_per_route():
    target2 = "https://other.example.com/hook"
    respx.post(TARGET).mock(return_value=httpx.Response(200))
    respx.post(target2).mock(return_value=httpx.Response(200))
    routes = [make_route(name="r1"), make_route(name="r2", target=target2)]
    results = dispatch_all(routes, {"event": "ping"})
    assert len(results) == 2
    assert all(isinstance(r, DispatchResult) for r in results)
    assert all(r.success for r in results)
