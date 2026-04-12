"""Integration tests for ranking config router."""

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from api.auth import get_api_key
from api.routers import ranking_config
from db.database import get_db


@pytest.fixture
def test_app(db_session):
    """Create test app with ranking_config router and mocked dependencies."""
    app = FastAPI()
    app.include_router(ranking_config.router, prefix="/api/v1")

    async def override_get_db():
        yield db_session

    async def override_get_api_key():
        return "test-key"

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_api_key] = override_get_api_key
    return app


@pytest.fixture
async def client(test_app):
    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


class TestRankingConfigAPI:
    """Integration tests for ranking config endpoints."""

    @pytest.mark.asyncio
    async def test_list_configs_empty(self, client):
        """Returns empty list when no configs exist."""
        resp = await client.get("/api/v1/ranking/configs")
        assert resp.status_code == 200
        assert resp.json() == []

    @pytest.mark.asyncio
    async def test_get_config_not_found(self, client):
        """Returns 404 for non-existent config."""
        resp = await client.get("/api/v1/ranking/configs/nonexistent-id")
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_create_config(self, client):
        """Creates a new ranking config."""
        resp = await client.post(
            "/api/v1/ranking/configs",
            json={
                "name": "Default Ranking",
                "description": "Test config",
                "alpha": 0.7,
            },
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "Default Ranking"
        assert data["alpha"] == 0.7

    @pytest.mark.asyncio
    async def test_delete_config_not_found(self, client):
        """Returns 404 when deleting non-existent config."""
        resp = await client.delete("/api/v1/ranking/configs/nonexistent-id")
        assert resp.status_code == 404
