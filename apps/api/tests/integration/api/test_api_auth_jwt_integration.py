"""Integration tests for auth_jwt router."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from api.deps.auth import get_current_active_user
from api.routers import auth_jwt
from db.database import get_db
from db.schemas import UserResponse


def _make_user_mock(**overrides):
    """Create a mock user with all required fields."""
    m = MagicMock()
    m.id = overrides.get("id", "user-001")
    m.email = overrides.get("email", "test@example.com")
    m.full_name = overrides.get("full_name", "Test User")
    m.role = overrides.get("role", "user")
    m.is_active = overrides.get("is_active", True)
    m.is_verified = overrides.get("is_verified", True)
    m.hashed_password = overrides.get("hashed_password", "$2b$12$hashed")
    m.failed_login_attempts = overrides.get("failed_login_attempts", 0)
    m.created_at = overrides.get("created_at", datetime(2025, 1, 1, tzinfo=timezone.utc))
    m.updated_at = overrides.get("updated_at", datetime(2025, 1, 2, tzinfo=timezone.utc))
    return m


@pytest.fixture
def test_app(db_session):
    """Create test app with auth_jwt router and mocked dependencies."""
    app = FastAPI()
    app.include_router(auth_jwt.router, prefix="/api/v1")

    async def override_get_db():
        yield db_session

    async def override_get_current_user():
        return UserResponse(
            id="admin-user-001",
            email="admin@example.com",
            roles=["admin"],
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


class TestAuthJWTAPI:
    """Integration tests for JWT auth endpoints."""

    @pytest.mark.asyncio
    async def test_register_user(self, client):
        """Registers a new user."""
        mock_user = _make_user_mock(email="newuser@example.com")
        mock_user_repo = AsyncMock()
        mock_user_repo.get_by_email.return_value = None
        mock_user_repo.create.return_value = mock_user

        mock_refresh_repo = AsyncMock()
        mock_refresh_repo.create.return_value = MagicMock()

        with (
            patch("api.routers.auth_jwt.UserRepository", return_value=mock_user_repo),
            patch("api.routers.auth_jwt.RefreshTokenRepository", return_value=mock_refresh_repo),
            patch("api.routers.auth_jwt.hash_password", return_value="hashed_pw"),
            patch("api.routers.auth_jwt.create_access_token", return_value="access_tok"),
            patch("api.routers.auth_jwt.generate_refresh_token", return_value="refresh_tok"),
            patch("api.routers.auth_jwt.get_access_token_expire_minutes", return_value=30),
            patch("api.routers.auth_jwt.get_refresh_token_expire_days", return_value=7),
            patch(
                "api.routers.auth_jwt.get_settings",
                return_value=MagicMock(
                    auth_registration_enabled=True,
                    auth_email_verification_required=False,
                    environment="test",
                ),
            ),
        ):
            resp = await client.post(
                "/api/v1/auth/register",
                json={
                    "email": "newuser@example.com",
                    "password": "SecurePass123!",
                    "full_name": "New User",
                },
            )
        assert resp.status_code == 201
        data = resp.json()
        assert "access_token" in data
        assert "refresh_token" in data

    @pytest.mark.asyncio
    async def test_register_duplicate_email(self, client):
        """Returns 409 for duplicate email."""
        mock_user_repo = AsyncMock()
        mock_user_repo.get_by_email.return_value = _make_user_mock()

        with (
            patch("api.routers.auth_jwt.UserRepository", return_value=mock_user_repo),
            patch(
                "api.routers.auth_jwt.get_settings",
                return_value=MagicMock(
                    auth_registration_enabled=True,
                    auth_email_verification_required=False,
                    environment="test",
                ),
            ),
        ):
            resp = await client.post(
                "/api/v1/auth/register",
                json={
                    "email": "test@example.com",
                    "password": "SecurePass123!",
                    "full_name": "Duplicate User",
                },
            )
        assert resp.status_code == 409

    @pytest.mark.asyncio
    async def test_login_invalid_credentials(self, client):
        """Returns 401 for invalid credentials."""
        mock_user_repo = AsyncMock()
        mock_user_repo.get_by_email.return_value = None

        with (
            patch("api.routers.auth_jwt.UserRepository", return_value=mock_user_repo),
            patch("api.routers.auth_jwt.get_audit_logger", return_value=MagicMock()),
        ):
            resp = await client.post(
                "/api/v1/auth/login",
                json={"email": "nonexistent@example.com", "password": "wrong"},
            )
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_logout(self, client):
        """Logs out successfully."""
        resp = await client.post("/api/v1/auth/logout")
        assert resp.status_code == 200
        data = resp.json()
        assert "logged out" in data["message"].lower()

    @pytest.mark.asyncio
    async def test_refresh_missing_token(self, client):
        """Returns 401 when no refresh token provided."""
        resp = await client.post("/api/v1/auth/refresh")
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_get_current_user(self, client):
        """Gets current user info."""
        resp = await client.get("/api/v1/auth/me")
        assert resp.status_code == 200
        data = resp.json()
        assert data["email"] == "admin@example.com"

    @pytest.mark.asyncio
    async def test_forgot_password_missing_email(self, client):
        """Returns 400 when email is missing."""
        resp = await client.post("/api/v1/auth/forgot-password", json={})
        assert resp.status_code == 400
