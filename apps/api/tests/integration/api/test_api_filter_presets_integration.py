"""Integration tests for filter presets router."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from api.deps.auth import get_current_active_user
from api.routers import filter_presets
from db.database import get_db
from db.schemas import UserResponse


def _make_preset_mock(**overrides):
    """Create a mock filter preset with all required fields as real values."""
    m = MagicMock()
    m.id = overrides.get("id", "preset-001")
    m.user_id = overrides.get("user_id", "test-user-123")
    m.name = overrides.get("name", "Test Preset")
    m.description = overrides.get("description", "Test description")
    m.filters = overrides.get("filters", {"city": "Krakow", "rooms": 2})
    m.is_default = overrides.get("is_default", False)
    m.last_used_at = overrides.get("last_used_at", None)
    m.use_count = overrides.get("use_count", 0)
    m.created_at = overrides.get("created_at", datetime(2025, 1, 1, tzinfo=timezone.utc))
    m.updated_at = overrides.get("updated_at", datetime(2025, 1, 2, tzinfo=timezone.utc))
    return m


@pytest.fixture
def test_app(db_session):
    """Create test app with filter_presets router and mocked dependencies."""
    app = FastAPI()
    app.include_router(filter_presets.router, prefix="/api/v1")

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


class TestFilterPresetsAPI:
    """Integration tests for filter presets endpoints."""

    @pytest.mark.asyncio
    async def test_create_filter_preset(self, client):
        """Creates a new filter preset."""
        mock_repo = AsyncMock()
        preset = _make_preset_mock()
        mock_repo.count_by_user.return_value = 0
        mock_repo.create.return_value = preset

        with patch("api.routers.filter_presets.FilterPresetRepository", return_value=mock_repo):
            resp = await client.post(
                "/api/v1/filter-presets",
                json={
                    "name": "Krakow 2BR",
                    "description": "2BR apartments in Krakow",
                    "filters": {"city": "Krakow", "rooms": 2},
                },
            )
        assert resp.status_code == 201

    @pytest.mark.asyncio
    async def test_list_filter_presets_empty(self, client):
        """Returns empty list when no presets exist."""
        mock_repo = AsyncMock()
        mock_repo.get_by_user.return_value = []
        mock_repo.count_by_user.return_value = 0

        with patch("api.routers.filter_presets.FilterPresetRepository", return_value=mock_repo):
            resp = await client.get("/api/v1/filter-presets")
        assert resp.status_code == 200
        data = resp.json()
        assert data["items"] == []
        assert data["total"] == 0

    @pytest.mark.asyncio
    async def test_get_filter_preset_not_found(self, client):
        """Returns 404 for non-existent preset."""
        mock_repo = AsyncMock()
        mock_repo.get_by_id.return_value = None

        with patch("api.routers.filter_presets.FilterPresetRepository", return_value=mock_repo):
            resp = await client.get("/api/v1/filter-presets/nonexistent-id")
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_update_filter_preset(self, client):
        """Updates a filter preset."""
        mock_repo = AsyncMock()
        preset = _make_preset_mock(name="Updated")
        mock_repo.update.return_value = preset

        with patch("api.routers.filter_presets.FilterPresetRepository", return_value=mock_repo):
            resp = await client.patch(
                "/api/v1/filter-presets/preset-001",
                json={"name": "Updated"},
            )
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_delete_filter_preset(self, client):
        """Deletes a filter preset."""
        mock_repo = AsyncMock()
        mock_repo.delete.return_value = True

        with patch("api.routers.filter_presets.FilterPresetRepository", return_value=mock_repo):
            resp = await client.delete("/api/v1/filter-presets/preset-001")
        assert resp.status_code == 204

    @pytest.mark.asyncio
    async def test_get_default_preset_not_found(self, client):
        """Returns 404 when no default preset is set."""
        mock_repo = AsyncMock()
        mock_repo.get_default.return_value = None

        with patch("api.routers.filter_presets.FilterPresetRepository", return_value=mock_repo):
            resp = await client.get("/api/v1/filter-presets/default")
        assert resp.status_code == 404
