"""
Tests for p95 latency monitoring middleware (Task #120).
"""

import time

from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.middleware.latency import (
    SLA_TARGETS,
    LatencyTracker,
    add_latency_middleware,
)

# ---------------------------------------------------------------------------
# LatencyTracker unit tests
# ---------------------------------------------------------------------------


class TestLatencyTracker:
    """Unit tests for the LatencyTracker class."""

    def test_record_and_get_p95_empty(self):
        tracker = LatencyTracker()
        assert tracker.get_p95("search") is None

    def test_record_and_get_p95_single(self):
        tracker = LatencyTracker()
        tracker.record("search", 100.0)
        assert tracker.get_p95("search") == 100.0

    def test_record_and_get_p95_percentile(self):
        tracker = LatencyTracker(window_seconds=300, max_samples=10_000)
        # Record 100 samples: 1..100 ms
        for i in range(1, 101):
            tracker.record("search", float(i))
        # p95 of 1..100 should be 95
        p95 = tracker.get_p95("search")
        assert p95 is not None
        assert p95 >= 94.0
        assert p95 <= 96.0

    def test_record_multiple_groups(self):
        tracker = LatencyTracker()
        tracker.record("search", 100.0)
        tracker.record("chat", 500.0)
        assert tracker.get_p95("search") == 100.0
        assert tracker.get_p95("chat") == 500.0

    def test_get_stats_structure(self):
        tracker = LatencyTracker()
        tracker.record("search", 100.0)
        stats = tracker.get_stats()
        assert "sla_targets" in stats
        assert "endpoints" in stats
        assert "search" in stats["endpoints"]
        assert "chat" in stats["endpoints"]
        search_stats = stats["endpoints"]["search"]
        assert search_stats["p95_ms"] == 100.0
        assert search_stats["sla_target_ms"] == SLA_TARGETS["search"]
        assert search_stats["sla_breached"] is False
        assert search_stats["sample_count"] == 1

    def test_get_stats_sla_breached(self):
        tracker = LatencyTracker()
        # search SLA is 2000ms, record a breach
        tracker.record("search", 5000.0)
        stats = tracker.get_stats()
        assert stats["endpoints"]["search"]["sla_breached"] is True

    def test_window_expiry(self):
        tracker = LatencyTracker(window_seconds=0.1)
        tracker.record("search", 100.0)
        time.sleep(0.15)
        assert tracker.get_p95("search") is None

    def test_max_samples_cap(self):
        tracker = LatencyTracker(max_samples=50)
        for i in range(200):
            tracker.record("search", float(i))
        stats = tracker.get_stats()
        assert stats["endpoints"]["search"]["sample_count"] <= 50


# ---------------------------------------------------------------------------
# Middleware integration tests
# ---------------------------------------------------------------------------


def _make_test_app() -> FastAPI:
    """Create a minimal FastAPI app with the latency middleware."""
    app = FastAPI()

    @app.post("/api/v1/search")
    async def search_endpoint():
        return {"results": []}

    @app.post("/api/v1/chat")
    async def chat_endpoint():
        return {"reply": "hi"}

    @app.get("/other")
    async def other_endpoint():
        return {"ok": True}

    add_latency_middleware(app)
    return app


class TestLatencyMiddleware:
    """Integration tests for the latency middleware."""

    def test_search_tracked(self):
        app = _make_test_app()
        client = TestClient(app)
        client.post("/api/v1/search")
        tracker = app.state.latency_tracker
        assert tracker.get_p95("search") is not None

    def test_chat_tracked(self):
        app = _make_test_app()
        client = TestClient(app)
        client.post("/api/v1/chat")
        tracker = app.state.latency_tracker
        assert tracker.get_p95("chat") is not None

    def test_other_not_tracked(self):
        app = _make_test_app()
        client = TestClient(app)
        client.get("/other")
        tracker = app.state.latency_tracker
        # "other" is not in SLA_TARGETS groups, so no latency tracked
        assert tracker.get_p95("search") is None
        assert tracker.get_p95("chat") is None


# ---------------------------------------------------------------------------
# Admin endpoint tests (use a lightweight test app to avoid complex imports)
# ---------------------------------------------------------------------------


def _make_admin_test_app(with_tracker: bool = True) -> FastAPI:
    """Create a minimal app with admin-style latency endpoint."""
    from fastapi import HTTPException, Request

    app = FastAPI()

    if with_tracker:
        add_latency_middleware(app)

    @app.get("/api/v1/admin/metrics/latency")
    async def latency_metrics(request: Request):
        tracker = getattr(request.app.state, "latency_tracker", None)
        if tracker is None:
            raise HTTPException(status_code=503, detail="Latency tracker not initialized")
        return tracker.get_stats()

    return app


class TestAdminLatencyEndpoint:
    """Tests for the GET /admin/metrics/latency endpoint."""

    def test_returns_latency_stats(self):
        app = _make_admin_test_app(with_tracker=True)
        app.state.latency_tracker.record("search", 150.0)
        app.state.latency_tracker.record("chat", 3000.0)

        client = TestClient(app)
        resp = client.get("/api/v1/admin/metrics/latency")
        assert resp.status_code == 200
        data = resp.json()
        assert "sla_targets" in data
        assert "endpoints" in data
        assert "search" in data["endpoints"]
        assert "chat" in data["endpoints"]
        assert data["endpoints"]["search"]["p95_ms"] == 150.0
        assert data["endpoints"]["chat"]["p95_ms"] == 3000.0
        assert data["endpoints"]["chat"]["sla_breached"] is False  # 3000 < 8000

    def test_sla_breach_detection(self):
        app = _make_admin_test_app(with_tracker=True)
        # chat SLA is 8000ms → record 9500ms
        app.state.latency_tracker.record("chat", 9500.0)

        client = TestClient(app)
        resp = client.get("/api/v1/admin/metrics/latency")
        data = resp.json()
        assert data["endpoints"]["chat"]["sla_breached"] is True

    def test_returns_503_without_tracker(self):
        app = _make_admin_test_app(with_tracker=False)
        client = TestClient(app)
        resp = client.get("/api/v1/admin/metrics/latency")
        assert resp.status_code == 503
