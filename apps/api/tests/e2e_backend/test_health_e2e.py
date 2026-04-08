"""
E2E tests for health and system endpoints.
"""

import pytest


@pytest.mark.asyncio
class TestHealthE2E:
    """Health check — validates the app boots and middleware stack works."""

    async def test_health_returns_ok(self, e2e_client):
        resp = await e2e_client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] in ("healthy", "degraded")
        assert "version" in data
        assert "uptime_seconds" in data

    async def test_health_with_dependencies(self, e2e_client):
        resp = await e2e_client.get("/health?include_dependencies=true")
        assert resp.status_code == 200
        data = resp.json()
        assert "dependencies" in data

    async def test_health_liveness(self, e2e_client):
        resp = await e2e_client.get("/health/live")
        assert resp.status_code == 200

    async def test_health_readiness(self, e2e_client):
        resp = await e2e_client.get("/health/ready")
        # May return 503 if vector store not initialized, but should not crash
        assert resp.status_code in (200, 503)

    async def test_openapi_docs_accessible(self, e2e_client):
        resp = await e2e_client.get("/docs")
        assert resp.status_code == 200

    async def test_openapi_json(self, e2e_client):
        resp = await e2e_client.get("/openapi.json")
        assert resp.status_code == 200
        data = resp.json()
        assert data["info"]["title"] == "AI Real Estate Assistant API V4"
        assert "/api/v1/search" in data["paths"]
        assert "/api/v1/chat" in data["paths"]
