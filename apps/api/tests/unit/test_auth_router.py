"""
Unit tests for auth router (api/routers/auth.py).

Tests cover:
- Request code endpoint (email validation, code generation, storage)
- Verify code endpoint (code validation, session creation)
- Get session endpoint (token validation, session retrieval)
- Error handling (disabled auth, invalid input)
"""

from unittest.mock import patch

import pytest
from fastapi import status

from api.routers.auth import router as auth_router


class MockSettings:
    """Mock settings for testing."""

    def __init__(self):
        self.auth_email_enabled = True
        self.auth_storage_dir = "/tmp/test_auth"
        self.auth_code_ttl_minutes = 10
        self.environment = "development"
        self.session_ttl_days = 7


class MockAuthStorage:
    """Mock AuthStorage for testing."""

    def __init__(self):
        self.codes = {}
        self.sessions = {}

    def set_code(self, email, code, ttl_minutes):
        self.codes[email] = {"code": code, "expires_at": "2099-01-01T00:00:00"}

    def get_code(self, email):
        return self.codes.get(email)

    def delete_code(self, email):
        if email in self.codes:
            del self.codes[email]

    def create_session(self, email, ttl_days):
        token = f"session_token_{email}"
        self.sessions[token] = {"email": email}
        return token

    def get_session(self, token):
        return self.sessions.get(token)


class TestRequestCodeEndpoint:
    """Test request code endpoint."""

    @pytest.mark.asyncio
    @patch("api.routers.auth.get_settings")
    @patch("api.routers.auth.AuthStorage")
    async def test_request_code_success(self, mock_storage_class, mock_settings):
        """Test successful code request with valid email."""
        # Setup mocks
        mock_settings.return_value = MockSettings()
        storage = MockAuthStorage()
        mock_storage_class.return_value = storage

        from fastapi import FastAPI
        from fastapi.testclient import TestClient

        test_app = FastAPI()
        test_app.include_router(auth_router)

        client = TestClient(test_app)
        response = client.post("/auth/request-code", json={"email": "test@example.com"})

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "code_sent"
        # In development mode, code is returned
        assert "code" in data
        # Verify code was stored
        stored = storage.get_code("test@example.com")
        assert stored is not None
        assert "code" in stored

    @pytest.mark.asyncio
    @patch("api.routers.auth.get_settings")
    async def test_request_code_disabled_auth(self, mock_settings):
        """Test request code when email auth is disabled."""
        settings = MockSettings()
        settings.auth_email_enabled = False
        mock_settings.return_value = settings

        from fastapi import FastAPI
        from fastapi.testclient import TestClient

        test_app = FastAPI()
        test_app.include_router(auth_router)

        client = TestClient(test_app)
        response = client.post("/auth/request-code", json={"email": "test@example.com"})

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        data = response.json()
        assert "detail" in data
        assert "disabled" in data["detail"].lower()

    @pytest.mark.asyncio
    async def test_request_code_invalid_email_format(self):
        """Test request code with invalid email format."""
        from fastapi import FastAPI
        from fastapi.testclient import TestClient

        test_app = FastAPI()
        test_app.include_router(auth_router)

        client = TestClient(test_app)
        response = client.post("/auth/request-code", json={"email": "invalid-email"})

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        data = response.json()
        assert "detail" in data
        assert "email" in data["detail"].lower()

    @pytest.mark.asyncio
    @patch("api.routers.auth.get_settings")
    @patch("api.routers.auth.AuthStorage")
    async def test_request_code_code_storage(self, mock_storage_class, mock_settings):
        """Test that code is properly stored with TTL."""
        mock_settings.return_value = MockSettings()
        storage = MockAuthStorage()
        mock_storage_class.return_value = storage

        from fastapi import FastAPI
        from fastapi.testclient import TestClient

        test_app = FastAPI()
        test_app.include_router(auth_router)

        client = TestClient(test_app)
        response = client.post("/auth/request-code", json={"email": "user@example.com"})

        assert response.status_code == status.HTTP_200_OK
        stored = storage.get_code("user@example.com")
        assert stored is not None
        assert "code" in stored

    @pytest.mark.asyncio
    @patch("api.routers.auth.get_settings")
    @patch("api.routers.auth.AuthStorage")
    async def test_request_code_missing_email(self, mock_storage_class, mock_settings):
        """Test request code with missing email field."""
        mock_settings.return_value = MockSettings()
        mock_storage_class.return_value = MockAuthStorage()

        from fastapi import FastAPI
        from fastapi.testclient import TestClient

        test_app = FastAPI()
        test_app.include_router(auth_router)

        client = TestClient(test_app)
        response = client.post("/auth/request-code", json={})

        # FastAPI validation should catch missing required field
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    @pytest.mark.asyncio
    @patch("api.routers.auth.get_settings")
    @patch("api.routers.auth.AuthStorage")
    async def test_request_code_empty_email(self, mock_storage_class, mock_settings):
        """Test request code with empty email string."""
        mock_settings.return_value = MockSettings()
        mock_storage_class.return_value = MockAuthStorage()

        from fastapi import FastAPI
        from fastapi.testclient import TestClient

        test_app = FastAPI()
        test_app.include_router(auth_router)

        client = TestClient(test_app)
        response = client.post("/auth/request-code", json={"email": ""})

        # Should fail validation (empty email)
        assert response.status_code == status.HTTP_400_BAD_REQUEST


class TestVerifyCodeEndpoint:
    """Test verify code endpoint."""

    @pytest.mark.asyncio
    @patch("api.routers.auth.get_settings")
    @patch("api.routers.auth.AuthStorage")
    async def test_verify_code_success(self, mock_storage_class, mock_settings):
        """Test successful code verification."""
        settings = MockSettings()
        mock_settings.return_value = settings

        storage = MockAuthStorage()
        # Pre-store a code
        storage.set_code("test@example.com", "123456", 10)
        mock_storage_class.return_value = storage

        from fastapi import FastAPI
        from fastapi.testclient import TestClient

        test_app = FastAPI()
        test_app.include_router(auth_router)

        client = TestClient(test_app)
        response = client.post(
            "/auth/verify-code", json={"email": "test@example.com", "code": "123456"}
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "session_token" in data
        assert data["user_email"] == "test@example.com"
        # Verify code was deleted
        assert storage.get_code("test@example.com") is None
        # Verify session was created
        session = storage.get_session(data["session_token"])
        assert session is not None
        assert session["email"] == "test@example.com"

    @pytest.mark.asyncio
    @patch("api.routers.auth.get_settings")
    async def test_verify_code_disabled_auth(self, mock_settings):
        """Test verify code when email auth is disabled."""
        settings = MockSettings()
        settings.auth_email_enabled = False
        mock_settings.return_value = settings

        from fastapi import FastAPI
        from fastapi.testclient import TestClient

        test_app = FastAPI()
        test_app.include_router(auth_router)

        client = TestClient(test_app)
        response = client.post(
            "/auth/verify-code", json={"email": "test@example.com", "code": "123456"}
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        data = response.json()
        assert "detail" in data
        assert "disabled" in data["detail"].lower()

    @pytest.mark.asyncio
    @patch("api.routers.auth.get_settings")
    @patch("api.routers.auth.AuthStorage")
    async def test_verify_code_invalid_format(self, mock_storage_class, mock_settings):
        """Test verify code with invalid code format (not 6 digits)."""
        mock_settings.return_value = MockSettings()
        mock_storage_class.return_value = MockAuthStorage()

        from fastapi import FastAPI
        from fastapi.testclient import TestClient

        test_app = FastAPI()
        test_app.include_router(auth_router)

        client = TestClient(test_app)
        response = client.post(
            "/auth/verify-code", json={"email": "test@example.com", "code": "abc"}
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        data = response.json()
        assert "detail" in data
        assert "code" in data["detail"].lower() or "format" in data["detail"].lower()

    @pytest.mark.asyncio
    @patch("api.routers.auth.get_settings")
    @patch("api.routers.auth.AuthStorage")
    async def test_verify_code_wrong_code(self, mock_storage_class, mock_settings):
        """Test verify code with wrong code."""
        mock_settings.return_value = MockSettings()

        storage = MockAuthStorage()
        storage.set_code("test@example.com", "123456", 10)
        mock_storage_class.return_value = storage

        from fastapi import FastAPI
        from fastapi.testclient import TestClient

        test_app = FastAPI()
        test_app.include_router(auth_router)

        client = TestClient(test_app)
        response = client.post(
            "/auth/verify-code", json={"email": "test@example.com", "code": "999999"}
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN
        data = response.json()
        assert "detail" in data

    @pytest.mark.asyncio
    @patch("api.routers.auth.get_settings")
    @patch("api.routers.auth.AuthStorage")
    async def test_verify_code_no_code_pending(self, mock_storage_class, mock_settings):
        """Test verify code when no code was requested for email."""
        mock_settings.return_value = MockSettings()
        storage = MockAuthStorage()
        mock_storage_class.return_value = storage

        from fastapi import FastAPI
        from fastapi.testclient import TestClient

        test_app = FastAPI()
        test_app.include_router(auth_router)

        client = TestClient(test_app)
        response = client.post(
            "/auth/verify-code", json={"email": "test@example.com", "code": "123456"}
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN
        data = response.json()
        assert "detail" in data

    @pytest.mark.asyncio
    @patch("api.routers.auth.get_settings")
    @patch("api.routers.auth.AuthStorage")
    async def test_verify_code_session_creation(self, mock_storage_class, mock_settings):
        """Test that verify code creates a session token."""
        mock_settings.return_value = MockSettings()

        storage = MockAuthStorage()
        storage.set_code("test@example.com", "123456", 10)
        mock_storage_class.return_value = storage

        from fastapi import FastAPI
        from fastapi.testclient import TestClient

        test_app = FastAPI()
        test_app.include_router(auth_router)

        client = TestClient(test_app)
        response = client.post(
            "/auth/verify-code", json={"email": "test@example.com", "code": "123456"}
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "session_token" in data
        token = data["session_token"]
        # Verify session exists
        session = storage.get_session(token)
        assert session is not None
        assert session["email"] == "test@example.com"


class TestGetSessionEndpoint:
    """Test get session endpoint."""

    @pytest.mark.asyncio
    @patch("api.routers.auth.get_settings")
    @patch("api.routers.auth.AuthStorage")
    async def test_get_session_valid_token(self, mock_storage_class, mock_settings):
        """Test get session with valid token."""
        mock_settings.return_value = MockSettings()

        storage = MockAuthStorage()
        # Create a session
        token = storage.create_session("test@example.com", 7)
        mock_storage_class.return_value = storage

        from fastapi import FastAPI
        from fastapi.testclient import TestClient

        test_app = FastAPI()
        test_app.include_router(auth_router)

        client = TestClient(test_app)
        response = client.get("/auth/session", headers={"X-Session-Token": token})

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "session_token" in data
        assert "user_email" in data

    @pytest.mark.asyncio
    @patch("api.routers.auth.get_settings")
    async def test_get_session_disabled_auth(self, mock_settings):
        """Test get session when email auth is disabled."""
        settings = MockSettings()
        settings.auth_email_enabled = False
        mock_settings.return_value = settings

        from fastapi import FastAPI
        from fastapi.testclient import TestClient

        test_app = FastAPI()
        test_app.include_router(auth_router)

        client = TestClient(test_app)
        response = client.get("/auth/session", headers={"X-Session-Token": "some-token"})

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        data = response.json()
        assert "detail" in data
        assert "disabled" in data["detail"].lower()

    @pytest.mark.asyncio
    @patch("api.routers.auth.get_settings")
    @patch("api.routers.auth.AuthStorage")
    async def test_get_session_no_token(self, mock_storage_class, mock_settings):
        """Test get session without token header."""
        mock_settings.return_value = MockSettings()
        mock_storage_class.return_value = MockAuthStorage()

        from fastapi import FastAPI
        from fastapi.testclient import TestClient

        test_app = FastAPI()
        test_app.include_router(auth_router)

        client = TestClient(test_app)
        response = client.get("/auth/session")

        # Should fail validation (missing token)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.asyncio
    @patch("api.routers.auth.get_settings")
    @patch("api.routers.auth.AuthStorage")
    async def test_get_session_invalid_token(self, mock_storage_class, mock_settings):
        """Test get session with invalid/expired token."""
        mock_settings.return_value = MockSettings()
        storage = MockAuthStorage()
        mock_storage_class.return_value = storage

        from fastapi import FastAPI
        from fastapi.testclient import TestClient

        test_app = FastAPI()
        test_app.include_router(auth_router)

        client = TestClient(test_app)
        response = client.get("/auth/session", headers={"X-Session-Token": "invalid_token"})

        assert response.status_code == status.HTTP_403_FORBIDDEN
        data = response.json()
        assert "detail" in data


class TestAuthRouterValidation:
    """Test auth router validation and configuration."""

    def test_router_tag(self):
        """Test that router has correct tag."""
        assert auth_router.tags == ["Auth"]

    def test_router_prefix(self):
        """Test that router endpoints are configured."""
        # Router should have endpoints registered
        assert len(auth_router.routes) >= 3

    @pytest.mark.asyncio
    @patch("api.routers.auth.get_settings")
    @patch("api.routers.auth.AuthStorage")
    async def test_email_validation_pattern(self, mock_storage_class, mock_settings):
        """Test that email validation follows expected pattern."""
        mock_settings.return_value = MockSettings()
        mock_storage_class.return_value = MockAuthStorage()

        from fastapi import FastAPI
        from fastapi.testclient import TestClient

        test_app = FastAPI()
        test_app.include_router(auth_router)

        client = TestClient(test_app)

        # Valid emails
        valid_emails = [
            "test@example.com",
            "user.name@example.com",
            "user+tag@example.co.uk",
        ]
        for email in valid_emails:
            response = client.post("/auth/request-code", json={"email": email})
            # Should pass email validation
            assert response.status_code in (
                status.HTTP_200_OK,
                status.HTTP_400_BAD_REQUEST,
            ), f"Unexpected status for {email}: {response.status_code}"
            if response.status_code == status.HTTP_400_BAD_REQUEST:
                # Make sure it's not an email error
                assert "email" not in response.json()["detail"].lower()

        # Invalid emails
        invalid_emails = [
            "not-an-email",
            "@example.com",
            "user@",
            "user space@example.com",
        ]
        for email in invalid_emails:
            response = client.post("/auth/request-code", json={"email": email})
            assert response.status_code == status.HTTP_400_BAD_REQUEST, f"Should fail for {email}"

    @pytest.mark.asyncio
    @patch("api.routers.auth.get_settings")
    @patch("api.routers.auth.AuthStorage")
    async def test_code_validation_pattern(self, mock_storage_class, mock_settings):
        """Test that code validation enforces 6-digit format."""
        mock_settings.return_value = MockSettings()
        storage = MockAuthStorage()
        storage.set_code("test@example.com", "123456", 10)
        mock_storage_class.return_value = storage

        from fastapi import FastAPI
        from fastapi.testclient import TestClient

        test_app = FastAPI()
        test_app.include_router(auth_router)

        client = TestClient(test_app)

        # Valid codes (6 digits)
        valid_codes = ["123456", "000000", "999999"]
        for code in valid_codes:
            response = client.post(
                "/auth/verify-code", json={"email": "test@example.com", "code": code}
            )
            assert response.status_code in (
                status.HTTP_200_OK,
                status.HTTP_403_FORBIDDEN,
            ), f"Failed for code {code}: {response.status_code}"

        # Invalid codes
        invalid_codes = ["12345", "1234567", "abcdef", "12 3456"]
        for code in invalid_codes:
            response = client.post(
                "/auth/verify-code", json={"email": "test@example.com", "code": code}
            )
            assert response.status_code == status.HTTP_400_BAD_REQUEST, (
                f"Should fail for code {code}"
            )
