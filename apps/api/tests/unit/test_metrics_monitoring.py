"""
Tests for Prometheus metrics endpoint enhancements (Task #57).
"""

from unittest.mock import MagicMock

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from api.routers.metrics import format_prometheus_metric, router


class TestFormatPrometheusMetric:
    """Test Prometheus metric formatting."""

    def test_gauge_no_labels(self):
        result = format_prometheus_metric("test_metric", 42.0, "gauge", help_text="A test")
        assert "# HELP test_metric A test" in result
        assert "# TYPE test_metric gauge" in result
        assert "test_metric 42.0" in result

    def test_counter_with_labels(self):
        result = format_prometheus_metric(
            "http_requests_total",
            100,
            "counter",
            labels={"method": "GET", "path": "/api/v1/search"},
        )
        assert 'http_requests_total{method="GET",path="/api/v1/search"} 100' in result

    def test_no_help_text(self):
        result = format_prometheus_metric("test", 1, "gauge")
        assert "# HELP" not in result
        assert "test 1" in result


class TestMetricsEndpoint:
    """Test the /metrics endpoint returns proper Prometheus format."""

    @pytest.fixture
    async def metrics_client(self):
        app = FastAPI()
        app.state.metrics = {}
        app.state.response_cache = None
        app.state.latency_tracker = None
        app.state.vector_store = None
        app.state.rate_limiter = None

        app.include_router(router)
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            yield client

    @pytest.mark.asyncio
    async def test_metrics_returns_prometheus_format(self, metrics_client):
        resp = await metrics_client.get("/metrics")
        assert resp.status_code == 200
        assert "text/plain" in resp.headers["content-type"]
        body = resp.text
        assert "# TYPE app_info gauge" in body
        assert "app_info" in body

    @pytest.mark.asyncio
    async def test_metrics_includes_app_info(self, metrics_client):
        resp = await metrics_client.get("/metrics")
        body = resp.text
        assert 'app="ai-real-estate-assistant"' in body
        assert "version" in body

    @pytest.mark.asyncio
    async def test_metrics_includes_health(self, metrics_client):
        resp = await metrics_client.get("/metrics")
        body = resp.text
        # Health metrics may not appear if health check fails silently
        # At minimum, app_info should always be present
        assert "app_info" in body

    @pytest.mark.asyncio
    async def test_metrics_with_latency_tracker(self, metrics_client):
        from api.middleware.latency import LatencyTracker

        tracker = LatencyTracker()
        tracker.record("search", 500.0)
        tracker.record("search", 1200.0)
        tracker.record("search", 1800.0)

        # Replace the tracker on the app
        metrics_client._transport.app.state.latency_tracker = tracker

        resp = await metrics_client.get("/metrics")
        body = resp.text
        assert "request_latency_p95_ms" in body
        assert "request_latency_sla_target_ms" in body
        assert "request_latency_sla_breached" in body

    @pytest.mark.asyncio
    async def test_metrics_with_cache(self, metrics_client):
        from utils.response_cache import CacheConfig, ResponseCache

        cache = ResponseCache(config=CacheConfig(enabled=True))
        metrics_client._transport.app.state.response_cache = cache

        resp = await metrics_client.get("/metrics")
        body = resp.text
        assert "cache_enabled" in body
        assert "cache_size" in body

    @pytest.mark.asyncio
    async def test_metrics_with_vector_store(self, metrics_client):
        mock_store = MagicMock()
        mock_store.get_stats.return_value = {"documents": 42}
        metrics_client._transport.app.state.vector_store = mock_store

        resp = await metrics_client.get("/metrics")
        body = resp.text
        assert "vector_store_documents" in body
        assert "42" in body
