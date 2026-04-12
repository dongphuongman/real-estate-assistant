"""Integration tests for model preferences router."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from api.deps.auth import get_current_active_user
from api.routers import model_preferences
from db.database import get_db
from db.schemas import UserResponse


def _make_preference_mock(**overrides):
    """Create a mock model preference with all required fields."""
    m = MagicMock()
    m.id = overrides.get("id", "pref-001")
    m.user_id = overrides.get("user_id", "test-user-123")
    m.task_type = overrides.get("task_type", "chat")
    m.provider = overrides.get("provider", "openai")
    m.model_name = overrides.get("model_name", "gpt-4o")
    m.fallback_chain = overrides.get("fallback_chain", None)
    m.is_active = overrides.get("is_active", True)
    m.created_at = overrides.get("created_at", datetime(2025, 1, 1, tzinfo=timezone.utc))
    m.updated_at = overrides.get("updated_at", datetime(2025, 1, 2, tzinfo=timezone.utc))
    return m


@pytest.fixture
def test_app(db_session):
    """Create test app with model_preferences router and mocked dependencies."""
    app = FastAPI()
    app.include_router(model_preferences.router, prefix="/api/v1")

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


class TestModelPreferencesAPI:
    """Integration tests for model preferences endpoints."""

    @pytest.mark.asyncio
    async def test_list_preferences_empty(self, client):
        """Returns empty list when no preferences exist."""
        mock_service = AsyncMock()
        mock_service.get_user_preferences.return_value = []

        with patch(
            "api.routers.model_preferences.ModelPreferenceService",
            return_value=mock_service,
        ):
            resp = await client.get("/api/v1/model-preferences")
        assert resp.status_code == 200
        data = resp.json()
        assert data["items"] == []
        assert data["total"] == 0

    @pytest.mark.asyncio
    async def test_get_task_preference(self, client):
        """Gets preference for a specific task type."""
        mock_service = AsyncMock()
        pref = _make_preference_mock(task_type="chat")
        mock_service.get_or_create_preference.return_value = pref

        with patch(
            "api.routers.model_preferences.ModelPreferenceService",
            return_value=mock_service,
        ):
            resp = await client.get("/api/v1/model-preferences/chat")
        assert resp.status_code == 200
        data = resp.json()
        assert data["task_type"] == "chat"
        assert data["provider"] == "openai"

    @pytest.mark.asyncio
    async def test_get_task_preference_invalid_type(self, client):
        """Returns 400 for invalid task type."""
        mock_service = AsyncMock()
        mock_service.get_or_create_preference.side_effect = ValueError("Invalid task type")

        with patch(
            "api.routers.model_preferences.ModelPreferenceService",
            return_value=mock_service,
        ):
            resp = await client.get("/api/v1/model-preferences/invalid_type")
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_create_preference(self, client):
        """Creates a new model preference."""
        mock_service = AsyncMock()
        pref = _make_preference_mock(task_type="search")
        mock_service.create_preference.return_value = pref

        with patch(
            "api.routers.model_preferences.ModelPreferenceService",
            return_value=mock_service,
        ):
            resp = await client.post(
                "/api/v1/model-preferences",
                json={
                    "task_type": "search",
                    "provider": "openai",
                    "model_name": "gpt-4o",
                },
            )
        assert resp.status_code == 201
        data = resp.json()
        assert data["task_type"] == "search"

    @pytest.mark.asyncio
    async def test_update_preference(self, client):
        """Updates an existing model preference."""
        mock_service = AsyncMock()
        pref = _make_preference_mock(provider="anthropic", model_name="claude-3-opus")
        mock_service.update_preference.return_value = pref

        with patch(
            "api.routers.model_preferences.ModelPreferenceService",
            return_value=mock_service,
        ):
            resp = await client.put(
                "/api/v1/model-preferences/pref-001",
                json={
                    "provider": "anthropic",
                    "model_name": "claude-3-opus",
                },
            )
        assert resp.status_code == 200
        data = resp.json()
        assert data["provider"] == "anthropic"

    @pytest.mark.asyncio
    async def test_delete_preference(self, client):
        """Deletes a model preference."""
        mock_service = AsyncMock()
        mock_service.delete_preference.return_value = True

        with patch(
            "api.routers.model_preferences.ModelPreferenceService",
            return_value=mock_service,
        ):
            resp = await client.delete("/api/v1/model-preferences/pref-001")
        assert resp.status_code == 204

    @pytest.mark.asyncio
    async def test_delete_preference_not_found(self, client):
        """Returns 404 when deleting non-existent preference."""
        mock_service = AsyncMock()
        mock_service.delete_preference.return_value = False

        with patch(
            "api.routers.model_preferences.ModelPreferenceService",
            return_value=mock_service,
        ):
            resp = await client.delete("/api/v1/model-preferences/nonexistent-id")
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_get_system_defaults(self, client):
        """Gets system default model preferences."""
        mock_service = MagicMock()
        mock_service.get_system_defaults.return_value = [
            {
                "task_type": "chat",
                "provider": "openai",
                "model_name": "gpt-4o",
                "description": "Default chat model",
                "cost_per_1m_input_tokens": 2.5,
                "cost_per_1m_output_tokens": 10.0,
            }
        ]
        mock_service.get_available_providers.return_value = ["openai", "anthropic", "google"]
        mock_service.get_available_models.return_value = {
            "openai": ["gpt-4o", "gpt-4o-mini"],
            "anthropic": ["claude-3-opus"],
        }

        with patch(
            "api.routers.model_preferences.ModelPreferenceService",
            return_value=mock_service,
        ):
            resp = await client.get("/api/v1/model-preferences/system/defaults")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["defaults"]) == 1
        assert data["defaults"][0]["task_type"] == "chat"
        assert len(data["available_providers"]) == 3

    @pytest.mark.asyncio
    async def test_get_cost_estimate(self, client):
        """Gets cost estimate for a model."""
        mock_service = MagicMock()
        mock_cost = MagicMock()
        mock_cost.provider = "openai"
        mock_cost.model_name = "gpt-4o"
        mock_cost.input_cost_per_1m = 2.5
        mock_cost.output_cost_per_1m = 10.0
        mock_cost.estimated_tokens_per_request = 1000
        mock_cost.estimated_cost_per_request = 0.005
        mock_service.get_cost_estimate.return_value = mock_cost

        with patch(
            "api.routers.model_preferences.ModelPreferenceService",
            return_value=mock_service,
        ):
            resp = await client.get(
                "/api/v1/model-preferences/system/cost-estimate",
                params={"provider": "openai", "model_name": "gpt-4o", "estimated_tokens": 1000},
            )
        assert resp.status_code == 200
        data = resp.json()
        assert data["provider"] == "openai"
        assert data["estimated_cost_per_request"] == 0.005
