"""Tests for hookbridge.metrics and hookbridge.metrics_handler."""

import json
from io import BytesIO
from unittest.mock import MagicMock, patch

import pytest

from hookbridge.metrics import MetricsCollector, get_collector
from hookbridge.metrics_handler import METRICS_PATH, add_metrics_route


# ---------------------------------------------------------------------------
# MetricsCollector unit tests
# ---------------------------------------------------------------------------


@pytest.fixture()
def collector() -> MetricsCollector:
    c = MetricsCollector()
    return c


def test_record_dispatch_success(collector: MetricsCollector) -> None:
    collector.record_dispatch("route-a", success=True, latency_ms=42.0)
    snap = {r["route_id"]: r for r in collector.snapshot()}
    assert snap["route-a"]["total_dispatched"] == 1
    assert snap["route-a"]["total_success"] == 1
    assert snap["route-a"]["total_failed"] == 0


def test_record_dispatch_failure(collector: MetricsCollector) -> None:
    collector.record_dispatch("route-b", success=False, latency_ms=10.0)
    snap = {r["route_id"]: r for r in collector.snapshot()}
    assert snap["route-b"]["total_failed"] == 1
    assert snap["route-b"]["total_success"] == 0


def test_avg_latency(collector: MetricsCollector) -> None:
    collector.record_dispatch("route-c", success=True, latency_ms=100.0)
    collector.record_dispatch("route-c", success=True, latency_ms=200.0)
    snap = {r["route_id"]: r for r in collector.snapshot()}
    assert snap["route-c"]["avg_latency_ms"] == pytest.approx(150.0)


def test_record_filtered(collector: MetricsCollector) -> None:
    collector.record_filtered("route-d")
    collector.record_filtered("route-d")
    snap = {r["route_id"]: r for r in collector.snapshot()}
    assert snap["route-d"]["total_filtered"] == 2


def test_reset_clears_all(collector: MetricsCollector) -> None:
    collector.record_dispatch("route-e", success=True, latency_ms=5.0)
    collector.reset()
    assert collector.snapshot() == []


def test_latency_capped_at_100(collector: MetricsCollector) -> None:
    for i in range(150):
        collector.record_dispatch("route-f", success=True, latency_ms=float(i))
    from hookbridge.metrics import RouteMetrics  # noqa: PLC0415
    m: RouteMetrics = collector._routes["route-f"]
    assert len(m.latencies_ms) == 100


def test_get_collector_returns_singleton() -> None:
    c1 = get_collector()
    c2 = get_collector()
    assert c1 is c2


# ---------------------------------------------------------------------------
# metrics_handler tests
# ---------------------------------------------------------------------------


def _make_metrics_handler(path: str = METRICS_PATH):
    """Build a minimal handler instance that serves GET requests."""
    from http.server import BaseHTTPRequestHandler  # noqa: PLC0415

    WrappedHandler = add_metrics_route(BaseHTTPRequestHandler)

    buf = BytesIO()
    handler = WrappedHandler.__new__(WrappedHandler)
    handler.path = path
    handler.wfile = buf
    handler.send_response = MagicMock()
    handler.send_header = MagicMock()
    handler.end_headers = MagicMock()
    return handler, buf


def test_metrics_endpoint_returns_200() -> None:
    handler, buf = _make_metrics_handler(METRICS_PATH)
    with patch("hookbridge.metrics_handler.get_collector") as mock_gc:
        mock_gc.return_value.snapshot.return_value = []
        handler.do_GET()
    handler.send_response.assert_called_once_with(200)


def test_metrics_endpoint_body_is_valid_json() -> None:
    handler, buf = _make_metrics_handler(METRICS_PATH)
    with patch("hookbridge.metrics_handler.get_collector") as mock_gc:
        mock_gc.return_value.snapshot.return_value = [{"route_id": "x"}]
        handler.do_GET()
    written = buf.getvalue()
    payload = json.loads(written)
    assert "routes" in payload


def test_unknown_get_path_returns_404() -> None:
    handler, _ = _make_metrics_handler("/unknown")
    handler.do_GET()
    handler.send_response.assert_called_once_with(404)
