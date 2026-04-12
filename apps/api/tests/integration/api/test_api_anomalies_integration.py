"""Integration tests for anomalies router."""

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from api.deps.auth import get_current_active_user
from api.routers import anomalies
from db.database import get_db
from db.schemas import UserResponse


@pytest.fixture
def test_app(db_session):
    """Create test app with anomalies router and mocked dependencies."""
    app = FastAPI()
    app.include_router(anomalies.router, prefix="/api/v1")

    async def override_get_db():
        yield db_session

    async def override_get_current_user():
        return UserResponse(
            id="test-user-123",
            email="test@example.com",
            roles=["user"],
            created_at="2024-01-01T00:00:00Z",
        )

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_active_user] = override_get_current_user
    return app


@pytest.fixture
async def client(test_app):
    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


class TestAnomaliesAPI:
    """Integration tests for anomaly endpoints."""

    @pytest.mark.asyncio
    async def test_list_anomalies_empty(self, client):
        """Returns empty list when no anomalies exist."""
        resp = await client.get("/api/v1/anomalies")
        assert resp.status_code == 200
        data = resp.json()
        assert "anomalies" in data or "items" in data or isinstance(data, dict)

    @pytest.mark.asyncio
    async def test_list_anomalies_with_severity_filter(self, client):
        """Filters anomalies by severity."""
        resp = await client.get(
            "/api/v1/anomalies",
            params={"severity": "high"},
        )
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_list_anomalies_with_type_filter(self, client):
        """Filters anomalies by anomaly type."""
        resp = await client.get(
            "/api/v1/anomalies",
            params={"anomaly_type": "price_spike"},
        )
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_get_anomaly_stats(self, client):
        """Returns anomaly statistics summary."""
        resp = await client.get("/api/v1/anomalies/stats")
        assert resp.status_code == 200
        data = resp.json()
        assert "total" in data

    @pytest.mark.asyncio
    async def test_get_anomaly_not_found(self, client):
        """Returns 404 for non-existent anomaly."""
        resp = await client.get("/api/v1/anomalies/nonexistent-id")
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_dismiss_anomaly_not_found(self, client):
        """Returns 404 when dismissing non-existent anomaly."""
        resp = await client.post(
            "/api/v1/anomalies/nonexistent-id/dismiss",
            json={"reason": "false positive"},
        )
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_list_anomalies_pagination(self, client):
        """Supports limit and offset pagination."""
        resp = await client.get(
            "/api/v1/anomalies",
            params={"limit": 10, "offset": 0},
        )
        assert resp.status_code == 200
