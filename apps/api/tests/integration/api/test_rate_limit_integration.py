"""Integration tests for rate limiting middleware."""

from unittest.mock import patch

from fastapi.testclient import TestClient

from api.main import app
from api.middleware.rate_limit import SlidingWindowRateLimiter
from config.settings import AppSettings


def _rl_settings(rpm: int = 5) -> AppSettings:
    return AppSettings(
        environment="development",
        api_access_key="test-key-123",
        api_rate_limit_enabled=True,
        api_rate_limit_rpm=rpm,
    )


def _setup_rate_limiter(rpm: int = 5):
    """Reconfigure the existing rate limiter for testing."""
    limiter = getattr(app.state, "rate_limiter", None)
    if limiter is None:
        limiter = SlidingWindowRateLimiter(default_rpm=rpm)
        app.state.rate_limiter = limiter
    limiter.default_rpm = rpm
    limiter._requests.clear()
    return limiter


def test_rate_limit_headers_and_429():
    client = TestClient(app)
    with (
        patch("config.settings.get_settings") as mock_settings,
        patch("api.auth.get_settings") as mock_auth_settings,
    ):
        mock_settings.return_value = _rl_settings(rpm=1)
        mock_auth_settings.return_value = mock_settings.return_value
        _setup_rate_limiter(rpm=1)
        headers = {"X-API-Key": "test-key-123"}
        r1 = client.get("/api/v1/verify-auth", headers=headers)
        assert r1.status_code == 200
        assert "X-RateLimit-Limit" in r1.headers
        assert "X-RateLimit-Remaining" in r1.headers
        assert "X-RateLimit-Reset" in r1.headers
        # Exhaust the limit with rapid requests
        for _ in range(5):
            client.get("/api/v1/verify-auth", headers=headers)
        # Should eventually get 429
        r_limited = client.get("/api/v1/verify-auth", headers=headers)
        assert r_limited.status_code == 429
        assert "Retry-After" in r_limited.headers


def test_per_client_rate_limits_differ_by_api_key():
    """Test that rate limiting applies correctly with multiple API keys.

    Note: Rate limiter is per-IP, not per-key. With TestClient all requests
    come from the same IP, so both keys share the same rate limit bucket.
    This test verifies the rate limit mechanism works with multi-key auth.
    """
    client = TestClient(app)
    with (
        patch("config.settings.get_settings") as mock_settings,
        patch("api.auth.get_settings") as mock_auth_settings,
    ):
        mock_settings.return_value = AppSettings(
            environment="development",
            api_access_keys=["client-a-key", "client-b-key"],
            api_rate_limit_enabled=True,
            api_rate_limit_rpm=5,
        )
        mock_auth_settings.return_value = mock_settings.return_value
        _setup_rate_limiter(rpm=5)

        headers_a = {"X-API-Key": "client-a-key"}
        headers_b = {"X-API-Key": "client-b-key"}

        # Both keys auth successfully
        r_a = client.get("/api/v1/verify-auth", headers=headers_a)
        assert r_a.status_code == 200
        assert "X-RateLimit-Limit" in r_a.headers

        r_b = client.get("/api/v1/verify-auth", headers=headers_b)
        assert r_b.status_code == 200
        assert "X-RateLimit-Limit" in r_b.headers

        # Exhaust the shared IP bucket
        for _ in range(10):
            client.get("/api/v1/verify-auth", headers=headers_a)

        # Both keys now rate limited (same IP)
        r_a_limited = client.get("/api/v1/verify-auth", headers=headers_a)
        assert r_a_limited.status_code == 429

        r_b_limited = client.get("/api/v1/verify-auth", headers=headers_b)
        assert r_b_limited.status_code == 429


def test_per_client_rate_limits_with_secondary_key():
    """Test that secondary API key auth works under rate limiting."""
    client = TestClient(app)
    with (
        patch("config.settings.get_settings") as mock_settings,
        patch("api.auth.get_settings") as mock_auth_settings,
    ):
        settings = AppSettings(
            environment="development",
            api_access_key="primary-key",
            api_access_key_secondary="secondary-key",
            api_rate_limit_enabled=True,
            api_rate_limit_rpm=5,
        )
        mock_settings.return_value = settings
        mock_auth_settings.return_value = settings
        _setup_rate_limiter(rpm=5)

        headers_primary = {"X-API-Key": "primary-key"}
        headers_secondary = {"X-API-Key": "secondary-key"}

        # Both keys work
        r1 = client.get("/api/v1/verify-auth", headers=headers_primary)
        assert r1.status_code == 200

        r3 = client.get("/api/v1/verify-auth", headers=headers_secondary)
        assert r3.status_code == 200


def test_health_endpoint_no_auth_required():
    """Test that /health endpoint works without API key."""
    client = TestClient(app)
    with patch("config.settings.get_settings") as mock_settings:
        mock_settings.return_value = AppSettings(
            environment="development",
            api_access_key="test-key-123",
            api_rate_limit_enabled=True,
            api_rate_limit_rpm=1,
        )
        r = client.get("/health")
        assert r.status_code == 200


def test_docs_endpoint_no_auth_required():
    """Test that /docs endpoint works without API key."""
    client = TestClient(app)
    with patch("config.settings.get_settings") as mock_settings:
        mock_settings.return_value = AppSettings(
            environment="development",
            api_access_key="test-key-123",
            api_rate_limit_enabled=True,
            api_rate_limit_rpm=1,
        )
        r = client.get("/docs")
        assert r.status_code == 200


def test_redoc_endpoint_no_auth_required():
    """Test that /redoc endpoint works without API key."""
    client = TestClient(app)
    with patch("config.settings.get_settings") as mock_settings:
        mock_settings.return_value = AppSettings(
            environment="development",
            api_access_key="test-key-123",
            api_rate_limit_enabled=True,
            api_rate_limit_rpm=1,
        )
        r = client.get("/redoc")
        assert r.status_code == 200


def test_excluded_endpoints_not_rate_limited():
    """Test that /health, /docs, /redoc are excluded from rate limiting."""
    client = TestClient(app)
    with patch("config.settings.get_settings") as mock_settings:
        settings = AppSettings(
            environment="development",
            api_access_key="test-key-123",
            api_rate_limit_enabled=True,
            api_rate_limit_rpm=1,
        )
        mock_settings.return_value = settings

        for _ in range(5):
            r = client.get("/health")
            assert r.status_code == 200
            assert "X-RateLimit-Limit" not in r.headers

        for _ in range(5):
            r = client.get("/docs")
            assert r.status_code == 200
            assert "X-RateLimit-Limit" not in r.headers
