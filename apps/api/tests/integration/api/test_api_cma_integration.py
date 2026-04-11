"""Integration tests for CMA (Comparative Market Analysis) router.

Tests full request/response cycles for the CMA API
using in-memory SQLite and dependency overrides.
"""

from unittest.mock import MagicMock

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from api.dependencies import get_vector_store
from api.deps.auth import get_current_active_user
from api.routers import cma
from db.database import get_db
from db.schemas import UserResponse


@pytest.fixture
def mock_vector_store():
    """Create a mock ChromaPropertyStore."""
    store = MagicMock()
    store.get_properties_by_ids = MagicMock(return_value=[])
    store.search = MagicMock(return_value=[])
    return store


@pytest.fixture
def test_app(db_session, mock_vector_store):
    """Create test app with CMA router."""
    app = FastAPI()
    app.include_router(cma.router, prefix="/api/v1/cma")

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
    app.dependency_overrides[get_vector_store] = lambda: mock_vector_store
    return app


@pytest.fixture
async def client(test_app):
    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


class TestCMAAPI:
    """Integration tests for CMA endpoints."""

    @pytest.mark.asyncio
    async def test_list_cma_reports_empty(self, client):
        resp = await client.get("/api/v1/cma/reports")
        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data
        assert data["total"] == 0

    @pytest.mark.asyncio
    async def test_create_cma_report(self, client):
        resp = await client.post(
            "/api/v1/cma/reports",
            json={
                "subject_property_id": "prop-001",
                "title": "Test CMA Report",
            },
        )
        # May return 201 or 200 depending on vector store mock
        assert resp.status_code in (200, 201)

    @pytest.mark.asyncio
    async def test_get_nonexistent_report(self, client):
        resp = await client.get("/api/v1/cma/reports/nonexistent-id")
        assert resp.status_code == 404
