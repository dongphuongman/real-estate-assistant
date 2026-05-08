"""
Unit tests for filter presets router (api/routers/filter_presets.py).

Tests cover:
- Create filter preset (success, limit exceeded, with default flag)
- List filter presets (empty, with data, pagination)
- Get default preset (found, not found)
- Get single preset (found, not found)
- Update preset (success, not found, set as default, partial update)
- Delete preset (success, not found)
- Mark preset as used (success, not found)
- Set preset as default (success, not found)
- Auth requirement enforcement
- Router configuration
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI, status
from httpx import ASGITransport, AsyncClient

from api.routers.filter_presets import router as filter_presets_router
from db.database import get_db

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


class _MockUser:
    """Mock authenticated user for dependency override."""

    def __init__(self) -> None:
        self.id = "test-user-123"
        self.email = "test@example.com"
        self.is_active = True


def _make_preset(
    preset_id: str = "preset-001",
    user_id: str = "test-user-123",
    name: str = "My Preset",
    description: str | None = None,
    filters: dict | None = None,
    is_default: bool = False,
    use_count: int = 0,
) -> MagicMock:
    """Create a mock FilterPresetDB-like object with all required attributes."""
    from datetime import datetime, timezone

    preset = MagicMock()
    preset.id = preset_id
    preset.user_id = user_id
    preset.name = name
    preset.description = description
    preset.filters = filters or {"city": "Berlin", "min_price": 100000}
    preset.is_default = is_default
    preset.use_count = use_count
    preset.last_used_at = None
    preset.created_at = datetime(2024, 1, 15, 12, 0, 0, tzinfo=timezone.utc)
    preset.updated_at = datetime(2024, 1, 15, 12, 0, 0, tzinfo=timezone.utc)
    # model_validate needs from_attributes-style access
    # Since FilterPresetResponse.model_validate reads attributes from the object,
    # MagicMock already provides attribute access.
    return preset


@pytest.fixture
async def presets_client(db_session):
    """Create an async HTTP client wired to an isolated app with the filter-presets router.

    Uses a real DB session but mocks the FilterPresetRepository so tests are
    unit-level and do not depend on DB schema or User FK constraints.
    """
    from api.deps.auth import get_current_active_user

    test_app = FastAPI()
    test_app.include_router(filter_presets_router)

    async def _override_get_db():
        yield db_session

    async def _override_user():
        return _MockUser()

    test_app.dependency_overrides[get_db] = _override_get_db
    test_app.dependency_overrides[get_current_active_user] = _override_user

    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client

    test_app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Router configuration
# ---------------------------------------------------------------------------


class TestFilterPresetsRouterConfiguration:
    """Test router metadata and route registration."""

    def test_router_prefix(self):
        assert filter_presets_router.prefix == "/filter-presets"

    def test_router_tag(self):
        assert "Filter Presets" in filter_presets_router.tags

    def test_routes_registered(self):
        paths = {route.path for route in filter_presets_router.routes}
        assert "/filter-presets" in paths
        assert "/filter-presets/default" in paths
        assert "/filter-presets/{preset_id}" in paths
        assert "/filter-presets/{preset_id}/use" in paths
        assert "/filter-presets/{preset_id}/set-default" in paths


# ---------------------------------------------------------------------------
# POST /filter-presets  -  create_filter_preset
# ---------------------------------------------------------------------------


class TestCreateFilterPreset:
    """Tests for POST /filter-presets."""

    @pytest.mark.asyncio
    async def test_create_success(self, presets_client):
        """Should create a filter preset and return 201."""
        preset = _make_preset(preset_id="new-1")
        with patch("api.routers.filter_presets.FilterPresetRepository") as MockRepo:
            mock_repo = MockRepo.return_value
            mock_repo.count_by_user = AsyncMock(return_value=0)
            mock_repo.create = AsyncMock(return_value=preset)

            response = await presets_client.post(
                "/filter-presets",
                json={
                    "name": "My Preset",
                    "description": "A test preset",
                    "filters": {"city": "Berlin", "min_price": 100000},
                    "is_default": False,
                },
            )

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["id"] == "new-1"
        assert data["name"] == "My Preset"
        assert data["user_id"] == "test-user-123"
        assert data["is_default"] is False

    @pytest.mark.asyncio
    async def test_create_with_default_flag(self, presets_client):
        """Should unset existing default and create new default preset."""
        existing_default = _make_preset(preset_id="old-default", is_default=True)
        new_preset = _make_preset(preset_id="new-default", is_default=True)

        with patch("api.routers.filter_presets.FilterPresetRepository") as MockRepo:
            mock_repo = MockRepo.return_value
            mock_repo.count_by_user = AsyncMock(return_value=1)
            mock_repo.get_default = AsyncMock(return_value=existing_default)
            mock_repo.set_default = AsyncMock(return_value=existing_default)
            mock_repo.create = AsyncMock(return_value=new_preset)

            response = await presets_client.post(
                "/filter-presets",
                json={
                    "name": "New Default",
                    "filters": {"city": "Munich"},
                    "is_default": True,
                },
            )

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["id"] == "new-default"
        mock_repo.get_default.assert_awaited_once_with("test-user-123")
        mock_repo.set_default.assert_awaited_once_with(existing_default, "test-user-123")

    @pytest.mark.asyncio
    async def test_create_with_default_no_existing_default(self, presets_client):
        """Should create default preset when no current default exists."""
        new_preset = _make_preset(preset_id="first-default", is_default=True)

        with patch("api.routers.filter_presets.FilterPresetRepository") as MockRepo:
            mock_repo = MockRepo.return_value
            mock_repo.count_by_user = AsyncMock(return_value=0)
            mock_repo.get_default = AsyncMock(return_value=None)
            mock_repo.create = AsyncMock(return_value=new_preset)

            response = await presets_client.post(
                "/filter-presets",
                json={
                    "name": "First Default",
                    "filters": {},
                    "is_default": True,
                },
            )

        assert response.status_code == status.HTTP_201_CREATED
        # set_default should NOT be called when there is no existing default
        mock_repo.set_default.assert_not_called()

    @pytest.mark.asyncio
    async def test_create_limit_exceeded(self, presets_client):
        """Should return 400 when preset limit is reached."""
        with patch("api.routers.filter_presets.FilterPresetRepository") as MockRepo:
            mock_repo = MockRepo.return_value
            mock_repo.count_by_user = AsyncMock(return_value=20)

            response = await presets_client.post(
                "/filter-presets",
                json={
                    "name": "Over Limit",
                    "filters": {},
                },
            )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "maximum" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_create_without_optional_fields(self, presets_client):
        """Should create preset with minimal required fields."""
        preset = _make_preset(preset_id="minimal-1", name="Minimal Preset", description=None)
        with patch("api.routers.filter_presets.FilterPresetRepository") as MockRepo:
            mock_repo = MockRepo.return_value
            mock_repo.count_by_user = AsyncMock(return_value=0)
            mock_repo.create = AsyncMock(return_value=preset)

            response = await presets_client.post(
                "/filter-presets",
                json={
                    "name": "Minimal Preset",
                },
            )

        assert response.status_code == status.HTTP_201_CREATED
        assert response.json()["name"] == "Minimal Preset"

    @pytest.mark.asyncio
    async def test_create_missing_name_returns_422(self, presets_client):
        """Should return 422 when name is missing."""
        response = await presets_client.post(
            "/filter-presets",
            json={"filters": {}},
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    @pytest.mark.asyncio
    async def test_create_empty_name_returns_422(self, presets_client):
        """Should return 422 when name is empty string."""
        response = await presets_client.post(
            "/filter-presets",
            json={"name": "", "filters": {}},
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


# ---------------------------------------------------------------------------
# GET /filter-presets  -  list_filter_presets
# ---------------------------------------------------------------------------


class TestListFilterPresets:
    """Tests for GET /filter-presets."""

    @pytest.mark.asyncio
    async def test_list_empty(self, presets_client):
        """Should return empty list when user has no presets."""
        with patch("api.routers.filter_presets.FilterPresetRepository") as MockRepo:
            mock_repo = MockRepo.return_value
            mock_repo.get_by_user = AsyncMock(return_value=[])
            mock_repo.count_by_user = AsyncMock(return_value=0)

            response = await presets_client.get("/filter-presets")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["items"] == []
        assert data["total"] == 0

    @pytest.mark.asyncio
    async def test_list_with_presets(self, presets_client):
        """Should return presets with total count."""
        presets = [_make_preset(preset_id=f"p-{i}", name=f"Preset {i}") for i in range(3)]
        with patch("api.routers.filter_presets.FilterPresetRepository") as MockRepo:
            mock_repo = MockRepo.return_value
            mock_repo.get_by_user = AsyncMock(return_value=presets)
            mock_repo.count_by_user = AsyncMock(return_value=3)

            response = await presets_client.get("/filter-presets")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["total"] == 3
        assert len(data["items"]) == 3
        assert data["items"][0]["id"] == "p-0"

    @pytest.mark.asyncio
    async def test_list_pagination(self, presets_client):
        """Should pass limit and offset to repository."""
        with patch("api.routers.filter_presets.FilterPresetRepository") as MockRepo:
            mock_repo = MockRepo.return_value
            mock_repo.get_by_user = AsyncMock(return_value=[])
            mock_repo.count_by_user = AsyncMock(return_value=10)

            response = await presets_client.get("/filter-presets?limit=5&offset=2")

        assert response.status_code == status.HTTP_200_OK
        mock_repo.get_by_user.assert_awaited_once_with("test-user-123", limit=5, offset=2)

    @pytest.mark.asyncio
    async def test_list_default_pagination_params(self, presets_client):
        """Should use default limit=50 and offset=0 when not specified."""
        with patch("api.routers.filter_presets.FilterPresetRepository") as MockRepo:
            mock_repo = MockRepo.return_value
            mock_repo.get_by_user = AsyncMock(return_value=[])
            mock_repo.count_by_user = AsyncMock(return_value=0)

            await presets_client.get("/filter-presets")

        mock_repo.get_by_user.assert_awaited_once_with("test-user-123", limit=50, offset=0)


# ---------------------------------------------------------------------------
# GET /filter-presets/default  -  get_default_preset
# ---------------------------------------------------------------------------


class TestGetDefaultPreset:
    """Tests for GET /filter-presets/default."""

    @pytest.mark.asyncio
    async def test_default_found(self, presets_client):
        """Should return the user's default preset."""
        default_preset = _make_preset(preset_id="def-1", is_default=True)
        with patch("api.routers.filter_presets.FilterPresetRepository") as MockRepo:
            mock_repo = MockRepo.return_value
            mock_repo.get_default = AsyncMock(return_value=default_preset)

            response = await presets_client.get("/filter-presets/default")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["id"] == "def-1"
        assert data["is_default"] is True

    @pytest.mark.asyncio
    async def test_default_not_found(self, presets_client):
        """Should return 404 when user has no default preset."""
        with patch("api.routers.filter_presets.FilterPresetRepository") as MockRepo:
            mock_repo = MockRepo.return_value
            mock_repo.get_default = AsyncMock(return_value=None)

            response = await presets_client.get("/filter-presets/default")

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "default" in response.json()["detail"].lower()


# ---------------------------------------------------------------------------
# GET /filter-presets/{preset_id}  -  get_filter_preset
# ---------------------------------------------------------------------------


class TestGetFilterPreset:
    """Tests for GET /filter-presets/{preset_id}."""

    @pytest.mark.asyncio
    async def test_get_found(self, presets_client):
        """Should return preset by ID."""
        preset = _make_preset(preset_id="get-1")
        with patch("api.routers.filter_presets.FilterPresetRepository") as MockRepo:
            mock_repo = MockRepo.return_value
            mock_repo.get_by_id = AsyncMock(return_value=preset)

            response = await presets_client.get("/filter-presets/get-1")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["id"] == "get-1"
        assert data["name"] == "My Preset"

    @pytest.mark.asyncio
    async def test_get_not_found(self, presets_client):
        """Should return 404 for nonexistent preset."""
        with patch("api.routers.filter_presets.FilterPresetRepository") as MockRepo:
            mock_repo = MockRepo.return_value
            mock_repo.get_by_id = AsyncMock(return_value=None)

            response = await presets_client.get("/filter-presets/nonexistent")

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "not found" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_get_scoped_to_user(self, presets_client):
        """Should pass user_id to repository for ownership scoping."""
        with patch("api.routers.filter_presets.FilterPresetRepository") as MockRepo:
            mock_repo = MockRepo.return_value
            mock_repo.get_by_id = AsyncMock(return_value=None)

            await presets_client.get("/filter-presets/some-id")

        mock_repo.get_by_id.assert_awaited_once_with("some-id", "test-user-123")


# ---------------------------------------------------------------------------
# PATCH /filter-presets/{preset_id}  -  update_filter_preset
# ---------------------------------------------------------------------------


class TestUpdateFilterPreset:
    """Tests for PATCH /filter-presets/{preset_id}."""

    @pytest.mark.asyncio
    async def test_update_name(self, presets_client):
        """Should update preset name and return updated preset."""
        original = _make_preset(preset_id="upd-1", name="Old Name")
        updated = _make_preset(preset_id="upd-1", name="New Name")

        with patch("api.routers.filter_presets.FilterPresetRepository") as MockRepo:
            mock_repo = MockRepo.return_value
            mock_repo.get_by_id = AsyncMock(return_value=original)
            mock_repo.update = AsyncMock(return_value=updated)

            response = await presets_client.patch(
                "/filter-presets/upd-1",
                json={"name": "New Name"},
            )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["name"] == "New Name"
        mock_repo.update.assert_awaited_once_with(original, name="New Name")

    @pytest.mark.asyncio
    async def test_update_not_found(self, presets_client):
        """Should return 404 when updating nonexistent preset."""
        with patch("api.routers.filter_presets.FilterPresetRepository") as MockRepo:
            mock_repo = MockRepo.return_value
            mock_repo.get_by_id = AsyncMock(return_value=None)

            response = await presets_client.patch(
                "/filter-presets/nonexistent",
                json={"name": "Whatever"},
            )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.asyncio
    async def test_update_set_as_default(self, presets_client):
        """Should unset other defaults and update preset."""
        original = _make_preset(preset_id="upd-def-1", is_default=False)
        updated = _make_preset(preset_id="upd-def-1", is_default=True)

        with patch("api.routers.filter_presets.FilterPresetRepository") as MockRepo:
            mock_repo = MockRepo.return_value
            mock_repo.get_by_id = AsyncMock(return_value=original)
            mock_repo.set_default = AsyncMock(return_value=updated)
            mock_repo.update = AsyncMock(return_value=updated)

            response = await presets_client.patch(
                "/filter-presets/upd-def-1",
                json={"is_default": True},
            )

        assert response.status_code == status.HTTP_200_OK
        mock_repo.set_default.assert_awaited_once_with(original, "test-user-123")
        # is_default is popped from update_data by the router, so update called without it
        mock_repo.update.assert_awaited_once_with(original)

    @pytest.mark.asyncio
    async def test_update_partial_filters_only(self, presets_client):
        """Should update only filters field."""
        original = _make_preset(preset_id="upd-filt-1")
        updated = _make_preset(
            preset_id="upd-filt-1",
            filters={"city": "Munich", "max_price": 500000},
        )

        with patch("api.routers.filter_presets.FilterPresetRepository") as MockRepo:
            mock_repo = MockRepo.return_value
            mock_repo.get_by_id = AsyncMock(return_value=original)
            mock_repo.update = AsyncMock(return_value=updated)

            response = await presets_client.patch(
                "/filter-presets/upd-filt-1",
                json={"filters": {"city": "Munich", "max_price": 500000}},
            )

        assert response.status_code == status.HTTP_200_OK
        mock_repo.update.assert_awaited_once_with(
            original,
            filters={"city": "Munich", "max_price": 500000},
        )

    @pytest.mark.asyncio
    async def test_update_empty_body(self, presets_client):
        """Should handle empty update body gracefully (no fields to update)."""
        original = _make_preset(preset_id="upd-empty-1")
        # model_dump(exclude_unset=True) with empty body -> empty dict
        with patch("api.routers.filter_presets.FilterPresetRepository") as MockRepo:
            mock_repo = MockRepo.return_value
            mock_repo.get_by_id = AsyncMock(return_value=original)
            mock_repo.update = AsyncMock(return_value=original)

            response = await presets_client.patch(
                "/filter-presets/upd-empty-1",
                json={},
            )

        assert response.status_code == status.HTTP_200_OK
        mock_repo.update.assert_awaited_once_with(original)


# ---------------------------------------------------------------------------
# DELETE /filter-presets/{preset_id}  -  delete_filter_preset
# ---------------------------------------------------------------------------


class TestDeleteFilterPreset:
    """Tests for DELETE /filter-presets/{preset_id}."""

    @pytest.mark.asyncio
    async def test_delete_success(self, presets_client):
        """Should delete preset and return 204."""
        preset = _make_preset(preset_id="del-1")

        with patch("api.routers.filter_presets.FilterPresetRepository") as MockRepo:
            mock_repo = MockRepo.return_value
            mock_repo.get_by_id = AsyncMock(return_value=preset)
            mock_repo.delete = AsyncMock(return_value=None)

            response = await presets_client.delete("/filter-presets/del-1")

        assert response.status_code == status.HTTP_204_NO_CONTENT
        mock_repo.delete.assert_awaited_once_with(preset)

    @pytest.mark.asyncio
    async def test_delete_not_found(self, presets_client):
        """Should return 404 when deleting nonexistent preset."""
        with patch("api.routers.filter_presets.FilterPresetRepository") as MockRepo:
            mock_repo = MockRepo.return_value
            mock_repo.get_by_id = AsyncMock(return_value=None)

            response = await presets_client.delete("/filter-presets/nonexistent")

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "not found" in response.json()["detail"].lower()


# ---------------------------------------------------------------------------
# POST /filter-presets/{preset_id}/use  -  mark_preset_used
# ---------------------------------------------------------------------------


class TestMarkPresetUsed:
    """Tests for POST /filter-presets/{preset_id}/use."""

    @pytest.mark.asyncio
    async def test_mark_used_success(self, presets_client):
        """Should increment usage count and return updated preset."""
        preset = _make_preset(preset_id="use-1", use_count=0)
        updated_preset = _make_preset(preset_id="use-1", use_count=1)

        with patch("api.routers.filter_presets.FilterPresetRepository") as MockRepo:
            mock_repo = MockRepo.return_value
            mock_repo.get_by_id = AsyncMock(return_value=preset)
            mock_repo.increment_usage = AsyncMock(return_value=updated_preset)

            response = await presets_client.post("/filter-presets/use-1/use")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["use_count"] == 1
        mock_repo.increment_usage.assert_awaited_once_with(preset)

    @pytest.mark.asyncio
    async def test_mark_used_not_found(self, presets_client):
        """Should return 404 when preset not found."""
        with patch("api.routers.filter_presets.FilterPresetRepository") as MockRepo:
            mock_repo = MockRepo.return_value
            mock_repo.get_by_id = AsyncMock(return_value=None)

            response = await presets_client.post("/filter-presets/nonexistent/use")

        assert response.status_code == status.HTTP_404_NOT_FOUND


# ---------------------------------------------------------------------------
# POST /filter-presets/{preset_id}/set-default  -  set_preset_default
# ---------------------------------------------------------------------------


class TestSetPresetDefault:
    """Tests for POST /filter-presets/{preset_id}/set-default."""

    @pytest.mark.asyncio
    async def test_set_default_success(self, presets_client):
        """Should set preset as default and return updated preset."""
        preset = _make_preset(preset_id="sdef-1", is_default=False)
        updated_preset = _make_preset(preset_id="sdef-1", is_default=True)

        with patch("api.routers.filter_presets.FilterPresetRepository") as MockRepo:
            mock_repo = MockRepo.return_value
            mock_repo.get_by_id = AsyncMock(return_value=preset)
            mock_repo.set_default = AsyncMock(return_value=updated_preset)

            response = await presets_client.post("/filter-presets/sdef-1/set-default")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["is_default"] is True
        mock_repo.set_default.assert_awaited_once_with(preset, "test-user-123")

    @pytest.mark.asyncio
    async def test_set_default_not_found(self, presets_client):
        """Should return 404 when preset not found."""
        with patch("api.routers.filter_presets.FilterPresetRepository") as MockRepo:
            mock_repo = MockRepo.return_value
            mock_repo.get_by_id = AsyncMock(return_value=None)

            response = await presets_client.post("/filter-presets/nonexistent/set-default")

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "not found" in response.json()["detail"].lower()


# ---------------------------------------------------------------------------
# Auth enforcement
# ---------------------------------------------------------------------------


class TestAuthRequirements:
    """Tests that all endpoints require authentication."""

    @pytest.mark.asyncio
    async def test_create_requires_auth(self):
        """POST /filter-presets should require authentication."""
        test_app = FastAPI()
        test_app.include_router(filter_presets_router)
        # No dependency overrides -> auth dependency will fail

        transport = ASGITransport(app=test_app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/filter-presets",
                json={"name": "Test", "filters": {}},
            )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.asyncio
    async def test_list_requires_auth(self):
        """GET /filter-presets should require authentication."""
        test_app = FastAPI()
        test_app.include_router(filter_presets_router)

        transport = ASGITransport(app=test_app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/filter-presets")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.asyncio
    async def test_get_default_requires_auth(self):
        """GET /filter-presets/default should require authentication."""
        test_app = FastAPI()
        test_app.include_router(filter_presets_router)

        transport = ASGITransport(app=test_app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/filter-presets/default")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.asyncio
    async def test_get_by_id_requires_auth(self):
        """GET /filter-presets/{id} should require authentication."""
        test_app = FastAPI()
        test_app.include_router(filter_presets_router)

        transport = ASGITransport(app=test_app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/filter-presets/some-id")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.asyncio
    async def test_update_requires_auth(self):
        """PATCH /filter-presets/{id} should require authentication."""
        test_app = FastAPI()
        test_app.include_router(filter_presets_router)

        transport = ASGITransport(app=test_app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.patch(
                "/filter-presets/some-id",
                json={"name": "Updated"},
            )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.asyncio
    async def test_delete_requires_auth(self):
        """DELETE /filter-presets/{id} should require authentication."""
        test_app = FastAPI()
        test_app.include_router(filter_presets_router)

        transport = ASGITransport(app=test_app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.delete("/filter-presets/some-id")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.asyncio
    async def test_mark_used_requires_auth(self):
        """POST /filter-presets/{id}/use should require authentication."""
        test_app = FastAPI()
        test_app.include_router(filter_presets_router)

        transport = ASGITransport(app=test_app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post("/filter-presets/some-id/use")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.asyncio
    async def test_set_default_requires_auth(self):
        """POST /filter-presets/{id}/set-default should require authentication."""
        test_app = FastAPI()
        test_app.include_router(filter_presets_router)

        transport = ASGITransport(app=test_app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post("/filter-presets/some-id/set-default")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


# ---------------------------------------------------------------------------
# Integration-style: full workflow
# ---------------------------------------------------------------------------


class TestFilterPresetsWorkflow:
    """End-to-end workflow tests across multiple endpoints."""

    @pytest.mark.asyncio
    async def test_create_get_update_delete_workflow(self, presets_client):
        """Full lifecycle: create -> get -> update -> use -> set-default -> delete."""
        preset = _make_preset(preset_id="wf-1", name="Workflow Preset")
        updated_preset = _make_preset(preset_id="wf-1", name="Updated Preset")
        used_preset = _make_preset(preset_id="wf-1", use_count=1)
        default_preset = _make_preset(preset_id="wf-1", is_default=True)

        # Create
        with patch("api.routers.filter_presets.FilterPresetRepository") as MockRepo:
            mock_repo = MockRepo.return_value
            mock_repo.count_by_user = AsyncMock(return_value=0)
            mock_repo.create = AsyncMock(return_value=preset)

            create_resp = await presets_client.post(
                "/filter-presets",
                json={"name": "Workflow Preset", "filters": {"city": "Berlin"}},
            )
        assert create_resp.status_code == status.HTTP_201_CREATED
        assert create_resp.json()["id"] == "wf-1"

        # Get
        with patch("api.routers.filter_presets.FilterPresetRepository") as MockRepo:
            mock_repo = MockRepo.return_value
            mock_repo.get_by_id = AsyncMock(return_value=preset)

            get_resp = await presets_client.get("/filter-presets/wf-1")
        assert get_resp.status_code == status.HTTP_200_OK
        assert get_resp.json()["name"] == "Workflow Preset"

        # Update
        with patch("api.routers.filter_presets.FilterPresetRepository") as MockRepo:
            mock_repo = MockRepo.return_value
            mock_repo.get_by_id = AsyncMock(return_value=preset)
            mock_repo.update = AsyncMock(return_value=updated_preset)

            upd_resp = await presets_client.patch(
                "/filter-presets/wf-1",
                json={"name": "Updated Preset"},
            )
        assert upd_resp.status_code == status.HTTP_200_OK
        assert upd_resp.json()["name"] == "Updated Preset"

        # Mark used
        with patch("api.routers.filter_presets.FilterPresetRepository") as MockRepo:
            mock_repo = MockRepo.return_value
            mock_repo.get_by_id = AsyncMock(return_value=updated_preset)
            mock_repo.increment_usage = AsyncMock(return_value=used_preset)

            use_resp = await presets_client.post("/filter-presets/wf-1/use")
        assert use_resp.status_code == status.HTTP_200_OK
        assert use_resp.json()["use_count"] == 1

        # Set default
        with patch("api.routers.filter_presets.FilterPresetRepository") as MockRepo:
            mock_repo = MockRepo.return_value
            mock_repo.get_by_id = AsyncMock(return_value=used_preset)
            mock_repo.set_default = AsyncMock(return_value=default_preset)

            def_resp = await presets_client.post("/filter-presets/wf-1/set-default")
        assert def_resp.status_code == status.HTTP_200_OK
        assert def_resp.json()["is_default"] is True

        # Delete
        with patch("api.routers.filter_presets.FilterPresetRepository") as MockRepo:
            mock_repo = MockRepo.return_value
            mock_repo.get_by_id = AsyncMock(return_value=default_preset)
            mock_repo.delete = AsyncMock(return_value=None)

            del_resp = await presets_client.delete("/filter-presets/wf-1")
        assert del_resp.status_code == status.HTTP_204_NO_CONTENT

    @pytest.mark.asyncio
    async def test_list_after_create_workflow(self, presets_client):
        """Create preset then verify it appears in listing."""
        preset = _make_preset(preset_id="list-wf-1")

        # Create
        with patch("api.routers.filter_presets.FilterPresetRepository") as MockRepo:
            mock_repo = MockRepo.return_value
            mock_repo.count_by_user = AsyncMock(return_value=0)
            mock_repo.create = AsyncMock(return_value=preset)

            await presets_client.post(
                "/filter-presets",
                json={"name": "List Test", "filters": {}},
            )

        # List
        with patch("api.routers.filter_presets.FilterPresetRepository") as MockRepo:
            mock_repo = MockRepo.return_value
            mock_repo.get_by_user = AsyncMock(return_value=[preset])
            mock_repo.count_by_user = AsyncMock(return_value=1)

            list_resp = await presets_client.get("/filter-presets")
        assert list_resp.status_code == status.HTTP_200_OK
        data = list_resp.json()
        assert data["total"] == 1
        assert data["items"][0]["id"] == "list-wf-1"
