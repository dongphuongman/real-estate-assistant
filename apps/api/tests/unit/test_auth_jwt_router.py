"""Unit tests for api/routers/auth_jwt.py.

Tests cover: rate limiting, helper functions, cookie management, and
endpoint-level behavior with mocked dependencies.
"""

import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI, status
from httpx import ASGITransport, AsyncClient

from api.routers.auth_jwt import (
    _auth_rate_limits,
    _check_auth_rate_limit,
    _clear_auth_cookies,
    _get_client_info,
    _get_client_ip,
    _set_auth_cookies,
)
from api.routers.auth_jwt import (
    router as auth_jwt_router,
)
from db.database import get_db


@pytest.fixture(autouse=True)
def _clear_rate_limits():
    _auth_rate_limits.clear()
    yield
    _auth_rate_limits.clear()


def _make_mock_user(
    id="user-123",
    email="test@example.com",
    role="user",
    is_active=True,
    is_verified=True,
    hashed_password="$2b$12$hash",
    failed_login_attempts=0,
):
    user = MagicMock()
    user.id = id
    user.email = email
    user.role = role
    user.is_active = is_active
    user.is_verified = is_verified
    user.hashed_password = hashed_password
    user.failed_login_attempts = failed_login_attempts
    return user


@pytest.fixture
def mock_session():
    session = AsyncMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    return session


@pytest.fixture
async def auth_client(mock_session):
    test_app = FastAPI()
    test_app.include_router(auth_jwt_router, prefix="/api/v1")

    async def override_get_db():
        yield mock_session

    test_app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
    test_app.dependency_overrides.clear()


# --- Helper Function Tests ---


class TestGetClientIp:
    def test_forwarded_for_header(self):
        request = MagicMock()
        request.headers = {"x-forwarded-for": "1.2.3.4, 5.6.7.8"}
        request.client = None
        assert _get_client_ip(request) == "1.2.3.4"

    def test_no_header_with_client(self):
        request = MagicMock()
        request.headers = {}
        request.client = MagicMock()
        request.client.host = "10.0.0.1"
        assert _get_client_ip(request) == "10.0.0.1"

    def test_no_header_no_client(self):
        request = MagicMock()
        request.headers = {}
        request.client = None
        assert _get_client_ip(request) == "unknown"


class TestGetClientInfo:
    def test_extracts_user_agent_and_ip(self):
        request = MagicMock()
        request.headers = {"user-agent": "TestBrowser/1.0", "x-forwarded-for": "1.2.3.4"}
        request.client = MagicMock()
        request.client.host = "10.0.0.1"
        ua, ip = _get_client_info(request)
        assert ua == "TestBrowser/1.0"
        assert ip == "1.2.3.4"

    def test_no_headers(self):
        request = MagicMock()
        request.headers = {}
        request.client = None
        ua, ip = _get_client_info(request)
        assert ua is None
        assert ip is None

    def test_comma_separated_ip(self):
        request = MagicMock()
        request.headers = {"x-forwarded-for": "1.2.3.4, 5.6.7.8"}
        request.client = MagicMock()
        request.client.host = "10.0.0.1"
        ua, ip = _get_client_info(request)
        assert ip == "1.2.3.4"


class TestAuthRateLimitHelper:
    def test_allows_under_limit(self):
        allowed, retry = _check_auth_rate_limit("test-key", max_requests=3)
        assert allowed is True
        assert retry == 0

    def test_blocks_over_limit(self):
        for _ in range(3):
            _check_auth_rate_limit("test-key-2", max_requests=3)
        allowed, retry = _check_auth_rate_limit("test-key-2", max_requests=3)
        assert allowed is False
        assert retry >= 1

    def test_separate_keys_independent(self):
        for _ in range(3):
            _check_auth_rate_limit("key-a", max_requests=3)
        allowed, _ = _check_auth_rate_limit("key-b", max_requests=3)
        assert allowed is True

    def test_window_expiry(self):
        # Fill limit, then shift timestamps into past
        from api.routers import auth_jwt as aj

        key = "test-expiry-key"
        aj._auth_rate_limits[key] = [time.time() - 100, time.time() - 100, time.time() - 100]
        allowed, _ = _check_auth_rate_limit(key, max_requests=3, window_seconds=10)
        assert allowed is True


class TestSetAuthCookies:
    def test_sets_cookies(self):
        response = MagicMock()
        with (
            patch("api.routers.auth_jwt.get_access_token_expire_minutes", return_value=15),
            patch("api.routers.auth_jwt.get_refresh_token_expire_days", return_value=7),
            patch("api.routers.auth_jwt.get_settings") as mock_settings,
        ):
            mock_settings.return_value.environment = "development"
            _set_auth_cookies(response, "access-tok", "refresh-tok", "csrf-tok")
        assert response.set_cookie.call_count == 3

    def test_no_csrf_token(self):
        response = MagicMock()
        with (
            patch("api.routers.auth_jwt.get_access_token_expire_minutes", return_value=15),
            patch("api.routers.auth_jwt.get_refresh_token_expire_days", return_value=7),
            patch("api.routers.auth_jwt.get_settings") as mock_settings,
        ):
            mock_settings.return_value.environment = "production"
            _set_auth_cookies(response, "access-tok", "refresh-tok")
        assert response.set_cookie.call_count == 2

    def test_production_secure_cookies(self):
        response = MagicMock()
        with (
            patch("api.routers.auth_jwt.get_access_token_expire_minutes", return_value=15),
            patch("api.routers.auth_jwt.get_refresh_token_expire_days", return_value=7),
            patch("api.routers.auth_jwt.get_settings") as mock_settings,
        ):
            mock_settings.return_value.environment = "production"
            _set_auth_cookies(response, "at", "rt")
        for call in response.set_cookie.call_args_list:
            assert call.kwargs.get("secure") is True


class TestClearAuthCookies:
    def test_clears_all_cookies(self):
        response = MagicMock()
        _clear_auth_cookies(response)
        assert response.delete_cookie.call_count == 3
        calls = response.delete_cookie.call_args_list
        deleted_keys = set()
        for call in calls:
            deleted_keys.add(call.kwargs.get("key", call.args[0] if call.args else ""))
        assert "access_token" in deleted_keys
        assert "refresh_token" in deleted_keys
        assert "csrf_token" in deleted_keys


# --- Endpoint Tests ---


class TestVerifyEmail:
    @pytest.mark.asyncio
    async def test_verify_email_missing_token(self, auth_client):
        response = await auth_client.post("/api/v1/auth/verify-email", json={})
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    @pytest.mark.asyncio
    async def test_verify_email_invalid_token(self, auth_client):
        with patch("db.repositories.EmailVerificationTokenRepository") as mock_repo_cls:
            mock_repo = AsyncMock()
            mock_repo_cls.return_value = mock_repo
            mock_token = MagicMock()
            mock_token.is_valid = False
            mock_repo.get_by_token.return_value = mock_token

            response = await auth_client.post(
                "/api/v1/auth/verify-email", json={"token": "bad-token"}
            )
            assert response.status_code == status.HTTP_400_BAD_REQUEST


class TestResendVerification:
    @pytest.mark.asyncio
    async def test_resend_missing_email(self, auth_client):
        response = await auth_client.post("/api/v1/auth/resend-verification", json={})
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    @pytest.mark.asyncio
    async def test_resend_user_not_found_returns_ok(self, auth_client):
        with patch("api.routers.auth_jwt.UserRepository") as mock_repo_cls:
            mock_repo = MagicMock()
            mock_repo_cls.return_value = mock_repo
            mock_repo.get_by_email = AsyncMock(return_value=None)

            response = await auth_client.post(
                "/api/v1/auth/resend-verification", json={"email": "nobody@example.com"}
            )
            assert response.status_code == status.HTTP_200_OK

    @pytest.mark.asyncio
    async def test_resend_already_verified_returns_ok(self, auth_client):
        with patch("api.routers.auth_jwt.UserRepository") as mock_repo_cls:
            mock_repo = MagicMock()
            mock_repo_cls.return_value = mock_repo
            mock_repo.get_by_email = AsyncMock(return_value=_make_mock_user(is_verified=True))

            response = await auth_client.post(
                "/api/v1/auth/resend-verification", json={"email": "test@example.com"}
            )
            assert response.status_code == status.HTTP_200_OK

    @pytest.mark.asyncio
    async def test_resend_sends_email_for_unverified_user(self, auth_client):
        with (
            patch("api.routers.auth_jwt.UserRepository") as mock_user_cls,
            patch("db.repositories.EmailVerificationTokenRepository") as mock_token_cls,
            patch("api.routers.auth_jwt.get_email_service") as mock_email_svc,
            patch("api.routers.auth_jwt.get_settings") as mock_settings,
            patch("core.jwt.generate_verification_token", return_value="vtoken123"),
        ):
            mock_user = MagicMock()
            mock_user_cls.return_value = mock_user
            mock_user.get_by_email = AsyncMock(return_value=_make_mock_user(is_verified=False))

            mock_token = MagicMock()
            mock_token_cls.return_value = mock_token
            mock_token.invalidate_for_user = AsyncMock()
            mock_token.create = AsyncMock()

            mock_settings_obj = MagicMock()
            mock_settings_obj.environment = "development"
            mock_settings_obj.frontend_url = "http://localhost:3000"
            mock_settings.return_value = mock_settings_obj

            mock_email = AsyncMock()
            mock_email_svc.return_value = mock_email

            response = await auth_client.post(
                "/api/v1/auth/resend-verification", json={"email": "test@example.com"}
            )
            assert response.status_code == status.HTTP_200_OK


class TestForgotPassword:
    @pytest.mark.asyncio
    async def test_forgot_missing_email(self, auth_client):
        response = await auth_client.post("/api/v1/auth/forgot-password", json={})
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    @pytest.mark.asyncio
    async def test_forgot_user_not_found(self, auth_client):
        with patch("api.routers.auth_jwt.UserRepository") as mock_repo_cls:
            mock_repo = MagicMock()
            mock_repo_cls.return_value = mock_repo
            mock_repo.get_by_email = AsyncMock(return_value=None)

            response = await auth_client.post(
                "/api/v1/auth/forgot-password", json={"email": "nobody@example.com"}
            )
            assert response.status_code == status.HTTP_200_OK

    @pytest.mark.asyncio
    async def test_forgot_sends_email(self, auth_client):
        with (
            patch("api.routers.auth_jwt.UserRepository") as mock_user_cls,
            patch("db.repositories.PasswordResetTokenRepository") as mock_token_cls,
            patch("api.routers.auth_jwt.get_email_service") as mock_email_svc,
            patch("api.routers.auth_jwt.get_settings") as mock_settings,
            patch("core.jwt.generate_password_reset_token", return_value="reset-tok-123"),
        ):
            mock_user = MagicMock()
            mock_user_cls.return_value = mock_user
            mock_user.get_by_email = AsyncMock(return_value=_make_mock_user())

            mock_token = MagicMock()
            mock_token_cls.return_value = mock_token
            mock_token.create = AsyncMock()

            mock_settings_obj = MagicMock()
            mock_settings_obj.environment = "development"
            mock_settings_obj.frontend_url = "http://localhost:3000"
            mock_settings.return_value = mock_settings_obj

            mock_email = AsyncMock()
            mock_email_svc.return_value = mock_email

            response = await auth_client.post(
                "/api/v1/auth/forgot-password", json={"email": "test@example.com"}
            )
            assert response.status_code == status.HTTP_200_OK
            mock_email.send_password_reset_email.assert_called_once()


class TestResetPassword:
    @pytest.mark.asyncio
    async def test_reset_missing_fields(self, auth_client):
        response = await auth_client.post("/api/v1/auth/reset-password", json={})
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    @pytest.mark.asyncio
    async def test_reset_weak_password(self, auth_client):
        with patch("core.password.validate_password_strength", return_value=(False, "Too short")):
            response = await auth_client.post(
                "/api/v1/auth/reset-password",
                json={"token": "some-token", "new_password": "short"},
            )
            assert response.status_code == status.HTTP_400_BAD_REQUEST
            assert "Too short" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_reset_invalid_token(self, auth_client):
        with (
            patch("core.password.validate_password_strength", return_value=(True, "")),
            patch("db.repositories.PasswordResetTokenRepository") as mock_repo_cls,
        ):
            mock_repo = AsyncMock()
            mock_repo_cls.return_value = mock_repo
            mock_repo.get_by_token.return_value = None

            response = await auth_client.post(
                "/api/v1/auth/reset-password",
                json={"token": "bad-token", "new_password": "Str0ngP@ssw0rd"},
            )
            assert response.status_code == status.HTTP_400_BAD_REQUEST
            assert "Invalid" in response.json()["detail"]


class TestGoogleOAuth:
    @pytest.mark.asyncio
    async def test_google_oauth_disabled(self, auth_client):
        with patch("api.routers.auth_jwt.get_settings") as mock_settings:
            mock_settings_obj = MagicMock()
            mock_settings_obj.auth_oauth_google_enabled = False
            mock_settings.return_value = mock_settings_obj

            response = await auth_client.get("/api/v1/auth/oauth/google")
            assert response.status_code == status.HTTP_403_FORBIDDEN

    @pytest.mark.asyncio
    async def test_google_oauth_not_configured(self, auth_client):
        with patch("api.routers.auth_jwt.get_settings") as mock_settings:
            mock_settings_obj = MagicMock()
            mock_settings_obj.auth_oauth_google_enabled = True
            mock_settings_obj.google_client_id = None
            mock_settings_obj.google_client_secret = None
            mock_settings.return_value = mock_settings_obj

            response = await auth_client.get("/api/v1/auth/oauth/google")
            assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR

    @pytest.mark.asyncio
    async def test_google_oauth_returns_url(self, auth_client):
        with patch("api.routers.auth_jwt.get_settings") as mock_settings:
            mock_settings_obj = MagicMock()
            mock_settings_obj.auth_oauth_google_enabled = True
            mock_settings_obj.google_client_id = "test-client-id"
            mock_settings_obj.google_client_secret = "test-secret"
            mock_settings_obj.google_redirect_uri = "http://localhost/callback"
            mock_settings_obj.environment = "development"
            mock_settings.return_value = mock_settings_obj

            with patch("core.oauth.GoogleOAuthProvider") as mock_provider_cls:
                mock_provider = MagicMock()
                mock_provider_cls.return_value = mock_provider
                mock_provider.generate_pkce_verifier.return_value = "verifier"
                mock_provider.generate_pkce_challenge.return_value = "challenge"
                mock_provider.get_authorization_url.return_value = (
                    "https://accounts.google.com/auth?state=abc"
                )

                response = await auth_client.get("/api/v1/auth/oauth/google")
                assert response.status_code == status.HTTP_200_OK
                assert "authorization_url" in response.json()


class TestOAuthCallback:
    @pytest.mark.asyncio
    async def test_callback_with_error(self, auth_client):
        response = await auth_client.get("/api/v1/auth/oauth/callback?error=access_denied")
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "access_denied" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_callback_missing_params(self, auth_client):
        response = await auth_client.get("/api/v1/auth/oauth/callback")
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "Missing" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_callback_invalid_state(self, auth_client):
        response = await auth_client.get("/api/v1/auth/oauth/callback?code=abc&state=wrong")
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "state" in response.json()["detail"].lower()


class TestAppleOAuth:
    @pytest.mark.asyncio
    async def test_apple_oauth_disabled(self, auth_client):
        with patch("api.routers.auth_jwt.get_settings") as mock_settings:
            mock_settings_obj = MagicMock()
            mock_settings_obj.auth_oauth_apple_enabled = False
            mock_settings.return_value = mock_settings_obj

            response = await auth_client.get("/api/v1/auth/oauth/apple")
            assert response.status_code == status.HTTP_403_FORBIDDEN

    @pytest.mark.asyncio
    async def test_apple_oauth_not_configured(self, auth_client):
        with patch("api.routers.auth_jwt.get_settings") as mock_settings:
            mock_settings_obj = MagicMock()
            mock_settings_obj.auth_oauth_apple_enabled = True
            mock_settings_obj.apple_client_id = None
            mock_settings_obj.apple_team_id = None
            mock_settings.return_value = mock_settings_obj

            response = await auth_client.get("/api/v1/auth/oauth/apple")
            assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR

    @pytest.mark.asyncio
    async def test_apple_oauth_no_private_key(self, auth_client):
        with patch("api.routers.auth_jwt.get_settings") as mock_settings:
            mock_settings_obj = MagicMock()
            mock_settings_obj.auth_oauth_apple_enabled = True
            mock_settings_obj.apple_client_id = "com.test.app"
            mock_settings_obj.apple_team_id = "team123"
            mock_settings_obj.apple_key_id = "key123"
            mock_settings_obj.apple_private_key_path = None
            mock_settings.return_value = mock_settings_obj

            response = await auth_client.get("/api/v1/auth/oauth/apple")
            assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR

    @pytest.mark.asyncio
    async def test_apple_oauth_returns_url(self, auth_client, tmp_path):
        key_file = tmp_path / "apple_key.p8"
        key_file.write_text("-----BEGIN PRIVATE KEY-----\nfake\n-----END PRIVATE KEY-----")

        with patch("api.routers.auth_jwt.get_settings") as mock_settings:
            mock_settings_obj = MagicMock()
            mock_settings_obj.auth_oauth_apple_enabled = True
            mock_settings_obj.apple_client_id = "com.test.app"
            mock_settings_obj.apple_team_id = "team123"
            mock_settings_obj.apple_key_id = "key123"
            mock_settings_obj.apple_private_key_path = str(key_file)
            mock_settings_obj.google_redirect_uri = "http://localhost/auth/google/callback"
            mock_settings_obj.environment = "development"
            mock_settings.return_value = mock_settings_obj

            with patch("core.oauth.AppleOAuthProvider") as mock_provider_cls:
                mock_provider = MagicMock()
                mock_provider_cls.return_value = mock_provider
                mock_provider.generate_pkce_verifier.return_value = "verifier"
                mock_provider.generate_pkce_challenge.return_value = "challenge"
                mock_provider.get_authorization_url.return_value = (
                    "https://appleid.apple.com/auth?state=xyz"
                )

                response = await auth_client.get("/api/v1/auth/oauth/apple")
                assert response.status_code == status.HTTP_200_OK
                assert "authorization_url" in response.json()

    @pytest.mark.asyncio
    async def test_apple_oauth_key_file_not_found(self, auth_client):
        with patch("api.routers.auth_jwt.get_settings") as mock_settings:
            mock_settings_obj = MagicMock()
            mock_settings_obj.auth_oauth_apple_enabled = True
            mock_settings_obj.apple_client_id = "com.test.app"
            mock_settings_obj.apple_team_id = "team123"
            mock_settings_obj.apple_key_id = "key123"
            mock_settings_obj.apple_private_key_path = "/nonexistent/key.p8"
            mock_settings.return_value = mock_settings_obj

            response = await auth_client.get("/api/v1/auth/oauth/apple")
            assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
