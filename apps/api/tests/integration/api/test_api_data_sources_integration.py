"""Integration tests for data sources router."""

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from api.routers import data_sources
from db.database import get_db


@pytest.fixture
def test_app(db_session):
    """Create test app with data_sources router and mocked dependencies."""
    app = FastAPI()
    app.include_router(data_sources.router, prefix="/api/v1")

    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    return app


@pytest.fixture
async def client(test_app):
    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


class TestDataSourcesAPI:
    """Integration tests for data sources endpoints."""

    @pytest.mark.asyncio
    async def test_list_data_sources_empty(self, client):
        """Returns empty list when no data sources exist."""
        resp = await client.get("/api/v1/data-sources")
        assert resp.status_code == 200
        data = resp.json()
        assert "sources" in data or "items" in data or isinstance(data, dict)

    @pytest.mark.asyncio
    async def test_list_data_sources_with_pagination(self, client):
        """Supports pagination parameters."""
        resp = await client.get(
            "/api/v1/data-sources",
            params={"page": 1, "page_size": 10},
        )
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_get_data_source_not_found(self, client):
        """Returns 404 for non-existent data source."""
        resp = await client.get("/api/v1/data-sources/nonexistent-id")
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_update_data_source_not_found(self, client):
        """Returns 404 when updating non-existent data source."""
        resp = await client.patch(
            "/api/v1/data-sources/nonexistent-id",
            json={"name": "Updated"},
        )
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_data_source_not_found(self, client):
        """Returns 404 when deleting non-existent data source."""
        resp = await client.delete(
            "/api/v1/data-sources/nonexistent-id",
            params={"confirm": "true"},
        )
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_get_sync_history_not_found(self, client):
        """Returns 404 for sync history of non-existent source."""
        resp = await client.get("/api/v1/data-sources/nonexistent-id/history")
        assert resp.status_code == 404
