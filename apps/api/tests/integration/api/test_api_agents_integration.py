"""Integration tests for agents router."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from api.deps.auth import get_current_active_user
from api.routers import agents
from db.database import get_db
from db.schemas import UserResponse


@pytest.fixture
def test_app(db_session):
    """Create test app with agents router and mocked dependencies."""
    app = FastAPI()
    app.include_router(agents.router, prefix="/api/v1")

    async def override_get_db():
        yield db_session

    async def override_get_current_user():
        return UserResponse(
            id="test-user-123",
            email="test@example.com",
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


class TestAgentsAPI:
    """Integration tests for agents endpoints."""

    @pytest.mark.asyncio
    async def test_list_agents_empty(self, client):
        """Returns empty list when no agents exist."""
        mock_repo = MagicMock()
        mock_repo.get_list = AsyncMock(return_value=[])
        mock_repo.count = AsyncMock(return_value=0)

        with patch("api.routers.agents.AgentProfileRepository", return_value=mock_repo):
            resp = await client.get("/api/v1/agents")
        assert resp.status_code == 200
        data = resp.json()
        assert data["items"] == []
        assert data["total"] == 0

    @pytest.mark.asyncio
    async def test_list_agents_with_filters(self, client):
        """Returns agents matching filters."""
        profile = MagicMock()
        profile.id = "agent-001"
        profile.user_id = "test-user-123"
        profile.agency_name = "Test Agency"
        profile.license_number = "LIC-123"
        profile.license_state = "PL"
        profile.professional_email = "agent@example.com"
        profile.professional_phone = "+48123456789"
        profile.office_address = "Krakow"
        profile.specialties = ["residential"]
        profile.service_areas = ["Krakow"]
        profile.property_types = ["apartment"]
        profile.languages = ["pl"]
        profile.average_rating = 4.5
        profile.total_reviews = 25
        profile.total_sales = 30
        profile.total_rentals = 15
        profile.is_verified = True
        profile.is_active = True
        profile.profile_image_url = None
        profile.bio = "Test bio"
        profile.created_at = datetime(2025, 1, 1, tzinfo=timezone.utc)
        profile.updated_at = datetime(2025, 1, 2, tzinfo=timezone.utc)
        mock_user = MagicMock()
        mock_user.full_name = "Test Agent"
        mock_user.email = "agent@example.com"
        profile.user = mock_user

        mock_repo = MagicMock()
        mock_repo.get_list = AsyncMock(return_value=[profile])
        mock_repo.count = AsyncMock(return_value=1)

        with patch("api.routers.agents.AgentProfileRepository", return_value=mock_repo):
            resp = await client.get(
                "/api/v1/agents",
                params={"city": "Krakow"},
            )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1

    @pytest.mark.asyncio
    async def test_get_agent_not_found(self, client):
        """Returns 404 for non-existent agent."""
        mock_repo = MagicMock()
        mock_repo.get_by_id = AsyncMock(return_value=None)

        with patch("api.routers.agents.AgentProfileRepository", return_value=mock_repo):
            resp = await client.get("/api/v1/agents/nonexistent-id")
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_get_agent_inactive(self, client):
        """Returns 404 for inactive agent."""
        profile = MagicMock()
        profile.is_active = False
        mock_repo = MagicMock()
        mock_repo.get_by_id = AsyncMock(return_value=profile)

        with patch("api.routers.agents.AgentProfileRepository", return_value=mock_repo):
            resp = await client.get("/api/v1/agents/inactive-agent")
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_get_own_profile_not_found(self, client):
        """Returns 404 when agent profile not found by agent_id=profile."""
        # NOTE: /agents/profile matches /{agent_id} with agent_id="profile"
        # because the {agent_id} route is registered before /profile in the router.
        # This test verifies 404 behavior when no agent with id "profile" exists.
        mock_repo = MagicMock()
        mock_repo.get_by_id = AsyncMock(return_value=None)

        with patch("api.routers.agents.AgentProfileRepository", return_value=mock_repo):
            resp = await client.get("/api/v1/agents/profile")
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_invalid_sort_field(self, client):
        """Returns 400 for invalid sort field."""
        mock_repo = MagicMock()

        with patch("api.routers.agents.AgentProfileRepository", return_value=mock_repo):
            resp = await client.get(
                "/api/v1/agents",
                params={"sort_by": "invalid_field"},
            )
        assert resp.status_code == 400
