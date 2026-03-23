"""API tests for model preferences endpoints (Task #87)."""

from datetime import UTC, datetime
from unittest.mock import patch
from uuid import uuid4

import pytest
from fastapi import status
from httpx import ASGITransport, AsyncClient


@pytest.fixture
def sample_preference():
    """Create a sample TaskModelPreference for testing."""
    from db.models import TaskModelPreference

    return TaskModelPreference(
        id=str(uuid4()),
        user_id="test-user-123",
        task_type="chat",
        provider="openai",
        model_name="gpt-4o-mini",
        fallback_chain=[{"provider": "anthropic", "model_name": "claude-3-5-sonnet-20241022"}],
        is_active=True,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )


class TestModelPreferencesAPI:
    """Tests for model preferences API endpoints."""

    @pytest.fixture
    async def test_client(self, db_session):
        """Create a test client with auth override."""
        from fastapi import FastAPI

        from api.deps.auth import get_current_active_user
        from api.routers import model_preferences
        from db.database import get_db
        from db.models import User

        # Create test app
        test_app = FastAPI()
        test_app.include_router(model_preferences.router, prefix="/api/v1")

        # Override DB dependency
        async def override_get_db():
            yield db_session

        # Mock user for auth
        async def override_get_current_user():
            return User(
                id="test-user-123",
                email="test@example.com",
                role="user",
                created_at=datetime.now(UTC),
            )

        test_app.dependency_overrides[get_db] = override_get_db
        test_app.dependency_overrides[get_current_active_user] = override_get_current_user

        transport = ASGITransport(app=test_app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            yield client

        # Cleanup
        test_app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_list_user_preferences_empty(self, test_client):
        """Test GET /model-preferences returns empty list when no preferences."""
        with patch(
            "services.model_preference_service.ModelPreferenceService.get_user_preferences"
        ) as mock_get:
            mock_get.return_value = []

            response = await test_client.get("/api/v1/model-preferences")

            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["total"] == 0
            assert data["items"] == []

    @pytest.mark.asyncio
    async def test_list_user_preferences_with_data(self, test_client, sample_preference):
        """Test GET /model-preferences returns user preferences."""
        with patch(
            "services.model_preference_service.ModelPreferenceService.get_user_preferences"
        ) as mock_get:
            mock_get.return_value = [sample_preference]

            response = await test_client.get("/api/v1/model-preferences")

            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["total"] == 1
            assert len(data["items"]) == 1
            assert data["items"][0]["task_type"] == "chat"

    @pytest.mark.asyncio
    async def test_get_task_preference_success(self, test_client, sample_preference):
        """Test GET /model-preferences/{task_type} returns preference."""
        with patch(
            "services.model_preference_service.ModelPreferenceService.get_or_create_preference"
        ) as mock_get:
            mock_get.return_value = sample_preference

            response = await test_client.get("/api/v1/model-preferences/chat")

            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["task_type"] == "chat"
            assert data["provider"] == "openai"
            assert data["model_name"] == "gpt-4o-mini"

    @pytest.mark.asyncio
    async def test_get_task_preference_invalid_task(self, test_client):
        """Test GET /model-preferences/{task_type} with invalid task type."""
        with patch(
            "services.model_preference_service.ModelPreferenceService.get_or_create_preference"
        ) as mock_get:
            mock_get.side_effect = ValueError("Invalid task_type")

            response = await test_client.get("/api/v1/model-preferences/invalid_task")

            assert response.status_code == status.HTTP_400_BAD_REQUEST

    @pytest.mark.asyncio
    async def test_create_preference_success(self, test_client, sample_preference):
        """Test POST /model-preferences creates a preference."""
        with patch(
            "services.model_preference_service.ModelPreferenceService.create_preference"
        ) as mock_create:
            mock_create.return_value = sample_preference

            response = await test_client.post(
                "/api/v1/model-preferences",
                json={
                    "task_type": "chat",
                    "provider": "openai",
                    "model_name": "gpt-4o-mini",
                    "is_active": True,
                },
            )

            assert response.status_code == status.HTTP_201_CREATED
            data = response.json()
            assert data["task_type"] == "chat"

    @pytest.mark.asyncio
    async def test_create_preference_with_fallback(self, test_client, sample_preference):
        """Test POST /model-preferences with fallback chain."""
        with patch(
            "services.model_preference_service.ModelPreferenceService.create_preference"
        ) as mock_create:
            mock_create.return_value = sample_preference

            response = await test_client.post(
                "/api/v1/model-preferences",
                json={
                    "task_type": "chat",
                    "provider": "openai",
                    "model_name": "gpt-4o-mini",
                    "fallback_chain": [
                        {
                            "provider": "anthropic",
                            "model_name": "claude-3-5-sonnet-20241022",
                        }
                    ],
                    "is_active": True,
                },
            )

            assert response.status_code == status.HTTP_201_CREATED

    @pytest.mark.asyncio
    async def test_create_preference_invalid_provider(self, test_client):
        """Test POST /model-preferences with invalid provider."""
        with patch(
            "services.model_preference_service.ModelPreferenceService.create_preference"
        ) as mock_create:
            mock_create.side_effect = ValueError("Invalid provider")

            response = await test_client.post(
                "/api/v1/model-preferences",
                json={
                    "task_type": "chat",
                    "provider": "invalid_provider",
                    "model_name": "some-model",
                },
            )

            assert response.status_code == status.HTTP_400_BAD_REQUEST

    @pytest.mark.asyncio
    async def test_create_preference_already_exists(self, test_client):
        """Test POST /model-preferences when preference already exists."""
        with patch(
            "services.model_preference_service.ModelPreferenceService.create_preference"
        ) as mock_create:
            mock_create.side_effect = ValueError("Preference already exists")

            response = await test_client.post(
                "/api/v1/model-preferences",
                json={
                    "task_type": "chat",
                    "provider": "openai",
                    "model_name": "gpt-4o-mini",
                },
            )

            assert response.status_code == status.HTTP_400_BAD_REQUEST

    @pytest.mark.asyncio
    async def test_update_preference_success(self, test_client, sample_preference):
        """Test PUT /model-preferences/{id} updates a preference."""
        # Modify the preference
        sample_preference.provider = "anthropic"
        sample_preference.model_name = "claude-3-5-sonnet-20241022"

        with patch(
            "services.model_preference_service.ModelPreferenceService.update_preference"
        ) as mock_update:
            mock_update.return_value = sample_preference

            response = await test_client.put(
                f"/api/v1/model-preferences/{sample_preference.id}",
                json={
                    "provider": "anthropic",
                    "model_name": "claude-3-5-sonnet-20241022",
                },
            )

            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["provider"] == "anthropic"

    @pytest.mark.asyncio
    async def test_update_preference_not_found(self, test_client):
        """Test PUT /model-preferences/{id} when preference not found."""
        with patch(
            "services.model_preference_service.ModelPreferenceService.update_preference"
        ) as mock_update:
            mock_update.return_value = None

            response = await test_client.put(
                "/api/v1/model-preferences/nonexistent-id",
                json={
                    "provider": "anthropic",
                    "model_name": "claude-3-5-sonnet-20241022",
                },
            )

            assert response.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.asyncio
    async def test_update_preference_invalid_provider(self, test_client, sample_preference):
        """Test PUT /model-preferences/{id} with invalid provider."""
        with patch(
            "services.model_preference_service.ModelPreferenceService.update_preference"
        ) as mock_update:
            mock_update.side_effect = ValueError("Invalid provider")

            response = await test_client.put(
                f"/api/v1/model-preferences/{sample_preference.id}",
                json={
                    "provider": "invalid_provider",
                    "model_name": "some-model",
                },
            )

            assert response.status_code == status.HTTP_400_BAD_REQUEST

    @pytest.mark.asyncio
    async def test_delete_preference_success(self, test_client):
        """Test DELETE /model-preferences/{id} deletes a preference."""
        with patch(
            "services.model_preference_service.ModelPreferenceService.delete_preference"
        ) as mock_delete:
            mock_delete.return_value = True

            response = await test_client.delete("/api/v1/model-preferences/some-preference-id")

            assert response.status_code == status.HTTP_204_NO_CONTENT

    @pytest.mark.asyncio
    async def test_delete_preference_not_found(self, test_client):
        """Test DELETE /model-preferences/{id} when preference not found."""
        with patch(
            "services.model_preference_service.ModelPreferenceService.delete_preference"
        ) as mock_delete:
            mock_delete.return_value = False

            response = await test_client.delete("/api/v1/model-preferences/nonexistent-id")

            assert response.status_code == status.HTTP_404_NOT_FOUND


class TestModelPreferencesSystemAPI:
    """Tests for system defaults endpoints."""

    @pytest.fixture
    async def test_client(self, db_session):
        """Create a test client with auth override."""
        from fastapi import FastAPI

        from api.deps.auth import get_current_active_user
        from api.routers import model_preferences
        from db.database import get_db
        from db.models import User

        test_app = FastAPI()
        test_app.include_router(model_preferences.router, prefix="/api/v1")

        async def override_get_db():
            yield db_session

        async def override_get_current_user():
            return User(
                id="test-user-123",
                email="test@example.com",
                role="user",
                created_at=datetime.now(UTC),
            )

        test_app.dependency_overrides[get_db] = override_get_db
        test_app.dependency_overrides[get_current_active_user] = override_get_current_user

        transport = ASGITransport(app=test_app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            yield client

        test_app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_get_system_defaults_success(self, test_client):
        """Test GET /model-preferences/system/defaults returns defaults."""
        response = await test_client.get("/api/v1/model-preferences/system/defaults")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "defaults" in data
        assert "available_providers" in data
        assert "available_models" in data
        assert len(data["defaults"]) == 5  # 5 task types

    @pytest.mark.asyncio
    async def test_get_system_defaults_includes_all_task_types(self, test_client):
        """Test that system defaults include all task types."""
        response = await test_client.get("/api/v1/model-preferences/system/defaults")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        task_types = [d["task_type"] for d in data["defaults"]]
        assert "chat" in task_types
        assert "search" in task_types
        assert "tools" in task_types
        assert "analysis" in task_types
        assert "embedding" in task_types

    @pytest.mark.asyncio
    async def test_get_cost_estimate_success(self, test_client):
        """Test GET /model-preferences/system/cost-estimate returns estimate."""
        response = await test_client.get(
            "/api/v1/model-preferences/system/cost-estimate",
            params={
                "provider": "openai",
                "model_name": "gpt-4o-mini",
                "estimated_tokens": 1000,
            },
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["provider"] == "openai"
        assert data["model_name"] == "gpt-4o-mini"
        assert data["estimated_tokens_per_request"] == 1000

    @pytest.mark.asyncio
    async def test_get_cost_estimate_default_tokens(self, test_client):
        """Test cost estimate uses default tokens when not specified."""
        response = await test_client.get(
            "/api/v1/model-preferences/system/cost-estimate",
            params={
                "provider": "openai",
                "model_name": "gpt-4o-mini",
            },
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["estimated_tokens_per_request"] == 1000

    @pytest.mark.asyncio
    async def test_get_cost_estimate_missing_params(self, test_client):
        """Test cost estimate with missing required parameters."""
        response = await test_client.get(
            "/api/v1/model-preferences/system/cost-estimate",
            params={},
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


class TestModelPreferencesAPIValidation:
    """Tests for input validation on model preferences endpoints."""

    @pytest.fixture
    async def test_client(self, db_session):
        """Create a test client with auth override."""
        from fastapi import FastAPI

        from api.deps.auth import get_current_active_user
        from api.routers import model_preferences
        from db.database import get_db
        from db.models import User

        test_app = FastAPI()
        test_app.include_router(model_preferences.router, prefix="/api/v1")

        async def override_get_db():
            yield db_session

        async def override_get_current_user():
            return User(
                id="test-user-123",
                email="test@example.com",
                role="user",
                created_at=datetime.now(UTC),
            )

        test_app.dependency_overrides[get_db] = override_get_db
        test_app.dependency_overrides[get_current_active_user] = override_get_current_user

        transport = ASGITransport(app=test_app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            yield client

        test_app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_create_preference_invalid_task_type(self, test_client):
        """Test POST with invalid task type."""
        response = await test_client.post(
            "/api/v1/model-preferences",
            json={
                "task_type": "invalid_task",
                "provider": "openai",
                "model_name": "gpt-4o-mini",
            },
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    @pytest.mark.asyncio
    async def test_create_preference_missing_required_fields(self, test_client):
        """Test POST with missing required fields."""
        response = await test_client.post(
            "/api/v1/model-preferences",
            json={
                "task_type": "chat",
                # Missing provider and model_name
            },
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    @pytest.mark.asyncio
    async def test_create_preference_empty_provider(self, test_client):
        """Test POST with empty provider."""
        response = await test_client.post(
            "/api/v1/model-preferences",
            json={
                "task_type": "chat",
                "provider": "",
                "model_name": "gpt-4o-mini",
            },
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    @pytest.mark.asyncio
    async def test_create_preference_too_long_fallback_chain(self, test_client):
        """Test POST with fallback chain exceeding 5 models."""
        response = await test_client.post(
            "/api/v1/model-preferences",
            json={
                "task_type": "chat",
                "provider": "openai",
                "model_name": "gpt-4o-mini",
                "fallback_chain": [
                    {"provider": "anthropic", "model_name": "claude-1"},
                    {"provider": "anthropic", "model_name": "claude-2"},
                    {"provider": "anthropic", "model_name": "claude-3"},
                    {"provider": "anthropic", "model_name": "claude-4"},
                    {"provider": "anthropic", "model_name": "claude-5"},
                    {"provider": "anthropic", "model_name": "claude-6"},
                ],
            },
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    @pytest.mark.asyncio
    async def test_cost_estimate_invalid_tokens(self, test_client):
        """Test cost estimate with invalid token count."""
        response = await test_client.get(
            "/api/v1/model-preferences/system/cost-estimate",
            params={
                "provider": "openai",
                "model_name": "gpt-4o-mini",
                "estimated_tokens": 0,  # Must be >= 1
            },
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    @pytest.mark.asyncio
    async def test_cost_estimate_tokens_too_large(self, test_client):
        """Test cost estimate with tokens exceeding max."""
        response = await test_client.get(
            "/api/v1/model-preferences/system/cost-estimate",
            params={
                "provider": "openai",
                "model_name": "gpt-4o-mini",
                "estimated_tokens": 2_000_000,  # Max is 1_000_000
            },
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


class TestModelPreferencesAPIUnauthenticated:
    """Tests for authentication requirements on model preferences endpoints."""

    @pytest.fixture
    async def unauth_client(self, db_session):
        """Create a test client without auth override."""
        from fastapi import FastAPI

        from api.routers import model_preferences
        from db.database import get_db

        test_app = FastAPI()
        test_app.include_router(model_preferences.router, prefix="/api/v1")

        async def override_get_db():
            yield db_session

        test_app.dependency_overrides[get_db] = override_get_db

        transport = ASGITransport(app=test_app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            yield client

        test_app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_list_requires_auth(self, unauth_client):
        """Test GET /model-preferences requires authentication."""
        response = await unauth_client.get("/api/v1/model-preferences")

        assert response.status_code in (
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_403_FORBIDDEN,
        )

    @pytest.mark.asyncio
    async def test_create_requires_auth(self, unauth_client):
        """Test POST /model-preferences requires authentication."""
        response = await unauth_client.post(
            "/api/v1/model-preferences",
            json={
                "task_type": "chat",
                "provider": "openai",
                "model_name": "gpt-4o-mini",
            },
        )

        assert response.status_code in (
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_403_FORBIDDEN,
        )

    @pytest.mark.asyncio
    async def test_update_requires_auth(self, unauth_client):
        """Test PUT /model-preferences/{id} requires authentication."""
        response = await unauth_client.put(
            "/api/v1/model-preferences/some-id",
            json={"provider": "anthropic"},
        )

        assert response.status_code in (
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_403_FORBIDDEN,
        )

    @pytest.mark.asyncio
    async def test_delete_requires_auth(self, unauth_client):
        """Test DELETE /model-preferences/{id} requires authentication."""
        response = await unauth_client.delete("/api/v1/model-preferences/some-id")

        assert response.status_code in (
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_403_FORBIDDEN,
        )

    @pytest.mark.asyncio
    async def test_system_defaults_requires_auth(self, unauth_client):
        """Test GET /model-preferences/system/defaults requires authentication."""
        response = await unauth_client.get("/api/v1/model-preferences/system/defaults")

        assert response.status_code in (
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_403_FORBIDDEN,
        )
