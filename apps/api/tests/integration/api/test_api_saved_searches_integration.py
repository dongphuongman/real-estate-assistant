"""Integration tests for saved searches router."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from api.deps.auth import get_current_active_user
from api.routers import saved_searches
from db.database import get_db
from db.schemas import UserResponse


def _make_search_mock(**overrides):
    """Create a mock saved search with all required fields as real values."""
    m = MagicMock()
    m.id = overrides.get("id", "search-001")
    m.user_id = overrides.get("user_id", "test-user-123")
    m.name = overrides.get("name", "Test Search")
    m.description = overrides.get("description", "Test description")
    m.filters = overrides.get("filters", {"city": "Krakow"})
    m.alert_frequency = overrides.get("alert_frequency", "daily")
    m.is_active = overrides.get("is_active", True)
    m.notify_on_new = overrides.get("notify_on_new", True)
    m.notify_on_price_drop = overrides.get("notify_on_price_drop", True)
    m.created_at = overrides.get("created_at", datetime(2025, 1, 1, tzinfo=timezone.utc))
    m.updated_at = overrides.get("updated_at", datetime(2025, 1, 2, tzinfo=timezone.utc))
    m.last_used_at = overrides.get("last_used_at", None)
    m.use_count = overrides.get("use_count", 0)
    return m


@pytest.fixture
def test_app(db_session):
    """Create test app with saved_searches router and mocked dependencies."""
    app = FastAPI()
    app.include_router(saved_searches.router, prefix="/api/v1")

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


class TestSavedSearchesAPI:
    """Integration tests for saved searches endpoints."""

    @pytest.mark.asyncio
    async def test_create_saved_search(self, client):
        """Creates a new saved search."""
        mock_repo = AsyncMock()
        search = _make_search_mock()
        mock_repo.create.return_value = search

        with patch("api.routers.saved_searches.SavedSearchRepository", return_value=mock_repo):
            resp = await client.post(
                "/api/v1/saved-searches",
                json={
                    "name": "Krakow Apartments",
                    "description": "2BR in Krakow",
                    "filters": {"city": "Krakow", "rooms": 2},
                    "alert_frequency": "daily",
                    "notify_on_new": True,
                    "notify_on_price_drop": True,
                },
            )
        assert resp.status_code == 201

    @pytest.mark.asyncio
    async def test_list_saved_searches_empty(self, client):
        """Returns empty list when no saved searches exist."""
        mock_repo = AsyncMock()
        mock_repo.get_by_user.return_value = []

        with patch("api.routers.saved_searches.SavedSearchRepository", return_value=mock_repo):
            resp = await client.get("/api/v1/saved-searches")
        assert resp.status_code == 200
        data = resp.json()
        assert data["items"] == []
        assert data["total"] == 0

    @pytest.mark.asyncio
    async def test_get_saved_search_not_found(self, client):
        """Returns 404 for non-existent saved search."""
        mock_repo = AsyncMock()
        mock_repo.get_by_id.return_value = None

        with patch("api.routers.saved_searches.SavedSearchRepository", return_value=mock_repo):
            resp = await client.get("/api/v1/saved-searches/nonexistent-id")
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_update_saved_search(self, client):
        """Updates a saved search."""
        mock_repo = AsyncMock()
        search = _make_search_mock(name="Updated Name")
        mock_repo.update.return_value = search

        with patch("api.routers.saved_searches.SavedSearchRepository", return_value=mock_repo):
            resp = await client.patch(
                "/api/v1/saved-searches/search-001",
                json={"name": "Updated Name"},
            )
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_delete_saved_search(self, client):
        """Deletes a saved search."""
        mock_repo = AsyncMock()
        mock_repo.delete.return_value = True

        with patch("api.routers.saved_searches.SavedSearchRepository", return_value=mock_repo):
            resp = await client.delete("/api/v1/saved-searches/search-001")
        assert resp.status_code == 204

    @pytest.mark.asyncio
    async def test_toggle_alert(self, client):
        """Toggles alert for a saved search."""
        mock_repo = AsyncMock()
        search = _make_search_mock()
        updated_search = _make_search_mock(is_active=True)
        mock_repo.get_by_id.return_value = search
        mock_repo.update.return_value = updated_search

        with patch("api.routers.saved_searches.SavedSearchRepository", return_value=mock_repo):
            resp = await client.post(
                "/api/v1/saved-searches/search-001/toggle-alert",
                params={"enabled": "true"},
            )
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_mark_used(self, client):
        """Marks a saved search as used."""
        mock_repo = AsyncMock()
        search = _make_search_mock()
        updated_search = _make_search_mock(use_count=1)
        mock_repo.get_by_id.return_value = search
        mock_repo.update.return_value = updated_search

        with patch("api.routers.saved_searches.SavedSearchRepository", return_value=mock_repo):
            resp = await client.post("/api/v1/saved-searches/search-001/use")
        assert resp.status_code == 200
