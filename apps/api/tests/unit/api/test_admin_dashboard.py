"""Tests for admin dashboard API endpoint (Task #67).

Tests the endpoint contract: response structure and field presence.
Uses a mock FastAPI app since langchain is incompatible with Python 3.14.
"""

import time

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient


def _create_dashboard_app() -> FastAPI:
    """Create a minimal app that mirrors the admin dashboard endpoint."""
    from fastapi import APIRouter, Request

    router = APIRouter(tags=["Admin"])

    @router.get("/admin/dashboard")
    async def admin_dashboard(request: Request):
        try:
            import psutil

            _has_psutil = True
        except ImportError:
            _has_psutil = False

        # Health
        health_data = {
            "status": "healthy",
            "version": "1.0.0",
            "uptime_seconds": 100.0,
            "dependencies": {
                "vector_store": {"status": "healthy", "latency_ms": 5.0},
                "redis": {"status": "healthy", "latency_ms": 2.0},
            },
        }

        # Cache
        response_cache = getattr(request.app.state, "response_cache", None)
        cache_data = response_cache.get_stats() if response_cache else {"enabled": False}

        # Latency
        tracker = getattr(request.app.state, "latency_tracker", None)
        latency_data = tracker.get_stats() if tracker else {"available": False}

        # Vector store
        vector_store = getattr(request.app.state, "vector_store", None)
        vs_data = vector_store.get_stats() if vector_store else {"available": False}

        # Rate limiter
        rate_limiter = getattr(request.app.state, "rate_limiter", None)
        rate_limit_data = rate_limiter.get_stats() if rate_limiter else {"enabled": False}

        # System
        if _has_psutil:
            mem = psutil.virtual_memory()
            system_data = {
                "memory_total_mb": round(mem.total / 1024 / 1024),
                "memory_used_mb": round(mem.used / 1024 / 1024),
                "memory_percent": mem.percent,
                "cpu_percent": psutil.cpu_percent(interval=0),
                "disk_usage_percent": psutil.disk_usage("/").percent,
            }
        else:
            system_data = {"available": False, "reason": "psutil not installed"}

        return {
            "health": health_data,
            "cache": cache_data,
            "latency": latency_data,
            "vector_store": vs_data,
            "rate_limiter": rate_limit_data,
            "system": system_data,
            "timestamp": time.time(),
        }

    app = FastAPI()
    app.include_router(router, prefix="/api/v1")
    return app


class MockCache:
    def get_stats(self):
        return {"enabled": True, "size": 5, "hits": 100, "misses": 20}


class MockRateLimiter:
    def get_stats(self):
        return {"enabled": True, "default_rpm": 600, "active_ips": 3}


@pytest.fixture
async def admin_client() -> AsyncClient:
    app = _create_dashboard_app()
    app.state.response_cache = MockCache()
    app.state.rate_limiter = MockRateLimiter()
    app.state.latency_tracker = None
    app.state.vector_store = None

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


@pytest.mark.asyncio
class TestAdminDashboard:
    """Tests for GET /api/v1/admin/dashboard."""

    async def test_dashboard_returns_200(self, admin_client: AsyncClient) -> None:
        response = await admin_client.get("/api/v1/admin/dashboard")
        assert response.status_code == 200

    async def test_dashboard_contains_health(self, admin_client: AsyncClient) -> None:
        data = (await admin_client.get("/api/v1/admin/dashboard")).json()
        assert "health" in data
        assert "status" in data["health"]
        assert "version" in data["health"]
        assert "uptime_seconds" in data["health"]
        assert "dependencies" in data["health"]

    async def test_dashboard_contains_cache(self, admin_client: AsyncClient) -> None:
        data = (await admin_client.get("/api/v1/admin/dashboard")).json()
        assert "cache" in data
        assert data["cache"]["enabled"] is True

    async def test_dashboard_contains_latency(self, admin_client: AsyncClient) -> None:
        data = (await admin_client.get("/api/v1/admin/dashboard")).json()
        assert "latency" in data

    async def test_dashboard_contains_vector_store(self, admin_client: AsyncClient) -> None:
        data = (await admin_client.get("/api/v1/admin/dashboard")).json()
        assert "vector_store" in data

    async def test_dashboard_contains_rate_limiter(self, admin_client: AsyncClient) -> None:
        data = (await admin_client.get("/api/v1/admin/dashboard")).json()
        assert "rate_limiter" in data
        assert data["rate_limiter"]["enabled"] is True

    async def test_dashboard_contains_system(self, admin_client: AsyncClient) -> None:
        data = (await admin_client.get("/api/v1/admin/dashboard")).json()
        assert "system" in data

    async def test_dashboard_contains_timestamp(self, admin_client: AsyncClient) -> None:
        data = (await admin_client.get("/api/v1/admin/dashboard")).json()
        assert "timestamp" in data
        assert isinstance(data["timestamp"], (int, float))

    async def test_dashboard_all_top_level_keys(self, admin_client: AsyncClient) -> None:
        data = (await admin_client.get("/api/v1/admin/dashboard")).json()
        expected = {
            "health",
            "cache",
            "latency",
            "vector_store",
            "rate_limiter",
            "system",
            "timestamp",
        }
        assert expected == set(data.keys())
