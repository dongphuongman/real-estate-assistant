"""Integration tests for push notifications router."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from api.deps.auth import get_current_active_user
from api.routers import push
from db.database import get_db
from db.schemas import UserResponse


def _make_subscription_mock(**overrides):
    """Create a mock push subscription with proper field values."""
    m = MagicMock()
    m.id = overrides.get("id", "sub-001")
    m.user_id = overrides.get("user_id", "test-user-123")
    m.endpoint = overrides.get("endpoint", "https://push.example.com/sub/123")
    m.p256dh = overrides.get("p256dh", "key123")
    m.auth = overrides.get("auth", "auth456")
    m.is_active = overrides.get("is_active", True)
    m.device_name = overrides.get("device_name", None)
    m.created_at = overrides.get("created_at", datetime(2025, 1, 1, tzinfo=timezone.utc))
    m.updated_at = overrides.get("updated_at", datetime(2025, 1, 2, tzinfo=timezone.utc))
    return m


def _make_settings_mock():
    """Create a mock settings with push enabled."""
    s = MagicMock()
    s.push_enabled = True
    s.vapid_public_key = "test-public-key"
    return s


@pytest.fixture
def test_app(db_session):
    """Create test app with push router and mocked dependencies."""
    app = FastAPI()
    app.include_router(push.router, prefix="/api/v1")

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


class TestPushAPI:
    """Integration tests for push notification endpoints."""

    @pytest.mark.asyncio
    async def test_subscribe(self, client):
        """Subscribes to push notifications."""
        mock_repo = MagicMock()
        sub = _make_subscription_mock()
        mock_repo.get_by_endpoint = AsyncMock(return_value=None)
        mock_repo.create = AsyncMock(return_value=sub)

        mock_settings = _make_settings_mock()

        with (
            patch("api.routers.push.PushSubscriptionRepository", return_value=mock_repo),
            patch("api.routers.push.settings", mock_settings),
        ):
            resp = await client.post(
                "/api/v1/push/subscribe",
                json={
                    "endpoint": "https://push.example.com/sub/123",
                    "keys": {"p256dh": "key123", "auth": "auth456"},
                },
            )
        assert resp.status_code in (200, 201)

    @pytest.mark.asyncio
    async def test_list_subscriptions_empty(self, client):
        """Returns empty list when no subscriptions exist."""
        mock_repo = AsyncMock()
        mock_repo.list_for_user.return_value = []

        with patch("api.routers.push.PushSubscriptionRepository", return_value=mock_repo):
            resp = await client.get("/api/v1/push/subscriptions")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_unsubscribe_not_found(self, client):
        """Returns 404 when unsubscribing non-existent subscription."""
        mock_repo = AsyncMock()
        mock_repo.delete.return_value = False

        with patch("api.routers.push.PushSubscriptionRepository", return_value=mock_repo):
            resp = await client.delete("/api/v1/push/subscriptions/nonexistent-id")
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_unsubscribe_idempotent(self, client):
        """Unsubscribe returns 204 even for unknown endpoints (idempotent)."""
        mock_repo = MagicMock()
        mock_repo.get_by_endpoint = AsyncMock(return_value=None)

        with patch("api.routers.push.PushSubscriptionRepository", return_value=mock_repo):
            resp = await client.delete(
                "/api/v1/push/unsubscribe",
                params={"endpoint": "https://push.example.com/sub/unknown"},
            )
        assert resp.status_code == 204
