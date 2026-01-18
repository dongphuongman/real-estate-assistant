from unittest.mock import patch

from fastapi.testclient import TestClient

from api.main import app
from config.settings import AppSettings


def _rl_settings() -> AppSettings:
    return AppSettings(
        environment="development",
        api_access_key="test-key-123",
        api_rate_limit_enabled=True,
        api_rate_limit_rpm=1,
    )


def test_rate_limit_headers_and_429():
    client = TestClient(app)
    with patch("config.settings.get_settings") as mock_settings, patch("api.auth.get_settings") as mock_auth_settings:
        mock_settings.return_value = _rl_settings()
        mock_auth_settings.return_value = mock_settings.return_value
        headers = {"X-API-Key": "test-key-123"}
        r1 = client.get("/api/v1/verify-auth", headers=headers)
        assert r1.status_code == 200
        assert "X-RateLimit-Limit" in r1.headers
        assert "X-RateLimit-Remaining" in r1.headers
        assert "X-RateLimit-Reset" in r1.headers
        r2 = client.get("/api/v1/verify-auth", headers=headers)
        assert r2.status_code == 429
        assert "Retry-After" in r2.headers
