"""
tests/test_metrics.py — Tests for services/metrics_service.py,
api/middleware/metrics.py, and GET /metrics (Phase 9, item 1).
"""
import pytest

from services.metrics_service import MetricsRegistry, render_exposition, http_requests_total
from tests.conftest import ADMIN_HEADERS


@pytest.fixture(autouse=True)
def _isolated_registry_state():
    """The module-level `registry` singleton persists across tests in the
    same process; snapshot and restore its per-metric internal dicts so
    counters from one test don't leak into another's assertions."""
    snapshots = []
    for metric in [http_requests_total]:
        snapshots.append((metric, dict(metric._values)))
    yield
    for metric, snapshot in snapshots:
        metric._values.clear()
        metric._values.update(snapshot)


def test_counter_increments():
    reg = MetricsRegistry()
    c = reg.counter("test_counter", "a test counter")
    c.inc()
    c.inc(2)
    assert c._values[()] == 3


def test_counter_with_labels_tracked_separately():
    reg = MetricsRegistry()
    c = reg.counter("test_counter", "help", label_names=("method",))
    c.inc(method="GET")
    c.inc(method="POST")
    c.inc(method="GET")
    assert c._values[("GET",)] == 2
    assert c._values[("POST",)] == 1


def test_gauge_set_and_dec():
    reg = MetricsRegistry()
    g = reg.gauge("test_gauge", "help")
    g.set(5)
    g.dec(2)
    assert g._values[()] == 3


def test_histogram_observe_buckets_and_count():
    reg = MetricsRegistry()
    h = reg.histogram("test_hist", "help", buckets=(0.1, 1.0))
    h.observe(0.05)
    h.observe(0.5)
    h.observe(5.0)
    assert h._counts[()] == 3
    assert h._sums[()] == pytest.approx(5.55)


def test_render_produces_prometheus_text_format():
    reg = MetricsRegistry()
    c = reg.counter("umbrella_test_total", "a counter for rendering")
    c.inc(3)
    text = reg.render()
    assert "# HELP umbrella_test_total a counter for rendering" in text
    assert "# TYPE umbrella_test_total counter" in text
    assert "umbrella_test_total 3.0" in text or "umbrella_test_total 3" in text


def test_render_escapes_label_values():
    reg = MetricsRegistry()
    c = reg.counter("test_counter", "help", label_names=("path",))
    c.inc(path='has"quote')
    text = reg.render()
    assert 'has\\"quote' in text


def test_render_exposition_includes_uptime():
    text = render_exposition()
    assert "umbrella_process_uptime_seconds" in text


@pytest.mark.asyncio
async def test_metrics_endpoint_requires_auth(client):
    response = await client.get("/metrics")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_metrics_endpoint_returns_prometheus_text_with_admin_key(client):
    response = await client.get("/metrics", headers=ADMIN_HEADERS)
    assert response.status_code == 200
    assert "text/plain" in response.headers["content-type"]
    assert "umbrella_http_requests_total" in response.text


@pytest.mark.asyncio
async def test_requests_are_recorded_with_route_template_not_raw_path(client):
    await client.get("/health")
    response = await client.get("/metrics", headers=ADMIN_HEADERS)
    assert 'path="/health"' in response.text
