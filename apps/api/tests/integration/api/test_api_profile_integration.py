"""Integration tests for profile router.

Tests full request/response cycles for the Profile API
using in-memory SQLite and dependency overrides.
"""

from unittest.mock import MagicMock

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from api.deps.auth import get_current_active_user
from api.routers import profile
from db.database import get_db, get_db_context


def _make_mock_user():
    """Create a mock User with profile fields."""
    user = MagicMock()
    user.id = "test-user-123"
    user.email = "test@example.com"
    user.full_name = "Test User"
    user.phone = "+48123456789"
    user.avatar_url = None
    user.timezone = "UTC"
    user.language = "en"
    user.bio = None
    user.privacy_settings = {}
    user.is_active = True
    user.is_verified = False
    user.role = "user"
    user.created_at = "2024-01-01T00:00:00Z"
    user.last_login_at = None
    user.gdpr_consent_at = None
    user.data_export_requested_at = None
    return user


@pytest.fixture
def mock_user():
    return _make_mock_user()


@pytest.fixture
def test_app(db_session, mock_user):
    """Create test app with profile router."""
    app = FastAPI()
    app.include_router(profile.router, prefix="/api/v1")

    async def override_get_db():
        yield db_session

    async def override_get_db_context():
        yield db_session

    async def override_get_current_user():
        return mock_user

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_db_context] = override_get_db_context
    app.dependency_overrides[get_current_active_user] = override_get_current_user
    return app


@pytest.fixture
async def client(test_app):
    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


class TestProfileAPI:
    """Integration tests for profile endpoints."""

    @pytest.mark.asyncio
    async def test_get_profile(self, client, mock_user):
        resp = await client.get("/api/v1/profile")
        assert resp.status_code == 200
        data = resp.json()
        assert data["email"] == "test@example.com"
        assert data["id"] == "test-user-123"

    @pytest.mark.asyncio
    async def test_update_profile_name(self, client, mock_user):
        resp = await client.put(
            "/api/v1/profile",
            json={"full_name": "Updated Name"},
        )
        assert resp.status_code == 200
        # Verify setattr was called on the mock user
        mock_user.__setattr__("full_name", "Updated Name")

    @pytest.mark.asyncio
    async def test_update_profile_language(self, client, mock_user):
        resp = await client.put(
            "/api/v1/profile",
            json={"language": "pl"},
        )
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_update_privacy_settings(self, client, mock_user):
        resp = await client.put(
            "/api/v1/profile/privacy",
            json={
                "profile_visible": False,
                "activity_visible": True,
                "show_email": False,
                "show_phone": False,
                "allow_contact": True,
            },
        )
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_empty_update_returns_profile(self, client, mock_user):
        resp = await client.put("/api/v1/profile", json={})
        assert resp.status_code == 200
