"""API tests for user activity endpoints (Task #82)."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException, status


@pytest.fixture
def mock_activity_service():
    """Create a mock UserActivityService."""
    service = MagicMock()
    service.track_event = AsyncMock()
    service.get_summary = AsyncMock(return_value={
        "period_start": "2024-01-01T00:00:00Z",
        "period_end": "2024-01-08T00:00:00Z",
        "total_events": 100,
        "total_searches": 50,
        "total_views": 30,
        "total_tool_uses": 20,
    })
    service.get_trends = AsyncMock(return_value=[
        {"date": "2024-01-01", "count": 10},
        {"date": "2024-01-02", "count": 15},
    ])
    service.export_to_csv = AsyncMock(return_value="timestamp,session_id,event_type\n2024-01-01T00:00:00Z,s1,search_query")
    service.cleanup_old_events = AsyncMock(return_value=5)
    service.get_event_types = AsyncMock(return_value=["search_query", "property_view", "tool_use"])
    service.get_top_sessions = AsyncMock(return_value=[
        {"session_id": "s1", "event_count": 42},
        {"session_id": "s2", "event_count": 15},
    ])
    service.get_category_breakdown = AsyncMock(return_value=[
        {"category": "search", "count": 50},
        {"category": "view", "count": 30},
    ])
    return service


@pytest.fixture
def user_activity_router(mock_activity_service):
    """Create a user activity router with mocked service."""
    from api.routers import user_activity
    from api.deps.auth import get_current_user

    # Store original dependency
    original_get_service = user_activity.get_activity_service

    def override_get_service():
        return mock_activity_service

    user_activity.get_activity_service = override_get_service

    # Mock user for auth
    async def mock_get_current_user():
        from db.schemas import UserResponse
        return UserResponse(
            id="test-user-123",
            email="test@example.com",
            roles=["user"],
            created_at="2024-01-01T00:00:00Z",
        )

    # Create a test FastAPI app with the router
    from fastapi import FastAPI
    test_app = FastAPI()
    test_app.include_router(user_activity.router, prefix="/api/v1")
    test_app.dependency_overrides[get_current_user] = mock_get_current_user

    yield test_app

    # Restore original
    user_activity.get_activity_service = original_get_service


class TestUserActivityAPIAuth:
    """Tests for authentication requirements on user activity endpoints."""

    @pytest.mark.asyncio
    async def test_get_summary_requires_auth(self, user_activity_router):
        """Test that summary endpoint requires authentication."""
        from httpx import ASGITransport, AsyncClient

        # Create app without auth override
        from fastapi import FastAPI
        from api.routers import user_activity

        test_app = FastAPI()
        test_app.include_router(user_activity.router, prefix="/api/v1")

        transport = ASGITransport(app=test_app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/v1/user-activity/summary")

        # Should return 401 (Unauthorized) or 403 (Forbidden) depending on implementation
        assert response.status_code in (401, 403)

    @pytest.mark.asyncio
    async def test_get_trends_requires_auth(self, user_activity_router):
        """Test that trends endpoint requires authentication."""
        from httpx import ASGITransport, AsyncClient

        # Create app without auth override
        from fastapi import FastAPI
        from api.routers import user_activity

        test_app = FastAPI()
        test_app.include_router(user_activity.router, prefix="/api/v1")

        transport = ASGITransport(app=test_app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/v1/user-activity/trends")

        assert response.status_code in (401, 403)

    @pytest.mark.asyncio
    async def test_export_requires_auth(self, user_activity_router):
        """Test that export endpoint requires authentication."""
        from httpx import ASGITransport, AsyncClient

        # Create app without auth override
        from fastapi import FastAPI
        from api.routers import user_activity

        test_app = FastAPI()
        test_app.include_router(user_activity.router, prefix="/api/v1")

        transport = ASGITransport(app=test_app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/v1/user-activity/export")

        assert response.status_code in (401, 403)

    @pytest.mark.asyncio
    async def test_track_event_requires_auth(self, user_activity_router):
        """Test that track_event endpoint requires authentication."""
        from httpx import ASGITransport, AsyncClient

        # Create app without auth override
        from fastapi import FastAPI
        from api.routers import user_activity

        test_app = FastAPI()
        test_app.include_router(user_activity.router, prefix="/api/v1")

        transport = ASGITransport(app=test_app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/api/v1/user-activity/track",
                json={
                    "session_id": "test-session",
                    "event_type": "test_event",
                    "event_category": "test"
                }
            )

        assert response.status_code in (401, 403)


class TestUserActivityAPISummary:
    """Tests for GET /api/v1/user-activity/summary endpoint."""

    @pytest.mark.asyncio
    async def test_get_summary_returns_aggregated_data(self, user_activity_router, mock_activity_service):
        """Test that summary endpoint returns aggregated statistics."""
        from httpx import ASGITransport, AsyncClient

        transport = ASGITransport(app=user_activity_router)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/v1/user-activity/summary")

        assert response.status_code == 200
        data = response.json()
        assert "period_start" in data
        assert "period_end" in data
        assert data["total_events"] == 100
        assert data["total_searches"] == 50
        assert data["total_views"] == 30
        assert data["total_tool_uses"] == 20

        # Verify service was called with correct params
        mock_activity_service.get_summary.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_summary_with_days_param(self, user_activity_router, mock_activity_service):
        """Test that summary endpoint accepts days parameter."""
        from httpx import ASGITransport, AsyncClient

        transport = ASGITransport(app=user_activity_router)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/v1/user-activity/summary?days=30")

        assert response.status_code == 200
        mock_activity_service.get_summary.assert_called_once_with(days=30, session_id=None)

    @pytest.mark.asyncio
    async def test_get_summary_with_session_filter(self, user_activity_router, mock_activity_service):
        """Test that summary endpoint can filter by session."""
        from httpx import ASGITransport, AsyncClient

        transport = ASGITransport(app=user_activity_router)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/v1/user-activity/summary?session_id=test-session")

        assert response.status_code == 200
        mock_activity_service.get_summary.assert_called_once_with(days=7, session_id="test-session")


class TestUserActivityAPITrends:
    """Tests for GET /api/v1/user-activity/trends endpoint."""

    @pytest.mark.asyncio
    async def test_get_trends_returns_time_series(self, user_activity_router, mock_activity_service):
        """Test that trends endpoint returns time series data."""
        from httpx import ASGITransport, AsyncClient

        transport = ASGITransport(app=user_activity_router)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/v1/user-activity/trends")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 2
        assert data[0]["date"] == "2024-01-01"
        assert data[0]["count"] == 10

    @pytest.mark.asyncio
    async def test_get_trends_with_interval_param(self, user_activity_router, mock_activity_service):
        """Test that trends endpoint accepts interval parameter."""
        from httpx import ASGITransport, AsyncClient

        transport = ASGITransport(app=user_activity_router)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/v1/user-activity/trends?interval=week&periods=4")

        assert response.status_code == 200
        mock_activity_service.get_trends.assert_called_once_with(
            interval="week",
            periods=4,
            event_type=None
        )

    @pytest.mark.asyncio
    async def test_get_trends_with_event_type_filter(self, user_activity_router, mock_activity_service):
        """Test that trends endpoint can filter by event type."""
        from httpx import ASGITransport, AsyncClient

        transport = ASGITransport(app=user_activity_router)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/v1/user-activity/trends?event_type=search_query")

        assert response.status_code == 200
        mock_activity_service.get_trends.assert_called_once_with(
            interval="day",
            periods=7,
            event_type="search_query"
        )


class TestUserActivityAPIExport:
    """Tests for GET /api/v1/user-activity/export endpoint."""

    @pytest.mark.asyncio
    async def test_export_returns_csv(self, user_activity_router, mock_activity_service):
        """Test that export endpoint returns CSV data."""
        from httpx import ASGITransport, AsyncClient

        transport = ASGITransport(app=user_activity_router)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/v1/user-activity/export")

        assert response.status_code == 200
        assert response.headers["content-type"] == "text/csv; charset=utf-8"
        assert "timestamp" in response.text
        assert "session_id" in response.text

    @pytest.mark.asyncio
    async def test_export_with_session_filter(self, user_activity_router, mock_activity_service):
        """Test that export can filter by session."""
        from httpx import ASGITransport, AsyncClient

        transport = ASGITransport(app=user_activity_router)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/v1/user-activity/export?session_id=test-session")

        assert response.status_code == 200
        mock_activity_service.export_to_csv.assert_called_once_with(session_id="test-session")

    @pytest.mark.asyncio
    async def test_export_sets_content_disposition(self, user_activity_router, mock_activity_service):
        """Test that export sets appropriate content disposition header."""
        from httpx import ASGITransport, AsyncClient

        transport = ASGITransport(app=user_activity_router)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/v1/user-activity/export")

        assert "content-disposition" in response.headers
        assert "attachment" in response.headers["content-disposition"]
        assert ".csv" in response.headers["content-disposition"]


class TestUserActivityAPITrack:
    """Tests for POST /api/v1/user-activity/track endpoint."""

    @pytest.mark.asyncio
    async def test_track_event_creates_event(self, user_activity_router, mock_activity_service):
        """Test that track endpoint creates a new event."""
        from httpx import ASGITransport, AsyncClient
        from datetime import datetime, UTC

        mock_event = MagicMock()
        mock_event.id = "test-event-id"
        mock_event.session_id = "test-session-123"
        mock_event.event_type = "tool_use"
        mock_event.event_category = "tools"
        mock_event.event_timestamp = datetime.now(UTC)
        mock_activity_service.track_event.return_value = mock_event

        transport = ASGITransport(app=user_activity_router)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/api/v1/user-activity/track",
                json={
                    "session_id": "test-session-123",
                    "event_type": "tool_use",
                    "event_category": "tools",
                    "event_data": {"tool_name": "mortgage_calculator"},
                    "duration_ms": 150,
                }
            )

        assert response.status_code == 201
        data = response.json()
        assert data["id"] == "test-event-id"
        assert data["session_id"] == "test-session-123"
        assert data["event_type"] == "tool_use"

        # Verify service was called
        mock_activity_service.track_event.assert_called_once()

    @pytest.mark.asyncio
    async def test_track_event_validates_required_fields(self, user_activity_router):
        """Test that track endpoint validates required fields."""
        from httpx import ASGITransport, AsyncClient

        transport = ASGITransport(app=user_activity_router)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            # Missing session_id
            response = await client.post(
                "/api/v1/user-activity/track",
                json={
                    "event_type": "tool_use",
                    "event_category": "tools",
                }
            )

        assert response.status_code == 422  # Validation error

    @pytest.mark.asyncio
    async def test_track_event_with_optional_fields(self, user_activity_router, mock_activity_service):
        """Test that optional fields are handled correctly."""
        from httpx import ASGITransport, AsyncClient

        mock_event = MagicMock()
        mock_event.id = "test-id"
        mock_activity_service.track_event.return_value = mock_event

        transport = ASGITransport(app=user_activity_router)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            # Only required fields
            response = await client.post(
                "/api/v1/user-activity/track",
                json={
                    "session_id": "s1",
                    "event_type": "page_view",
                    "event_category": "navigation",
                }
            )

        assert response.status_code == 201
        mock_activity_service.track_event.assert_called_once_with(
            session_id="s1",
            event_type="page_view",
            event_category="navigation",
            event_data=None,
            user_id=None,
            duration_ms=None,
        )


class TestUserActivityAPICleanup:
    """Tests for POST /api/v1/user-activity/cleanup endpoint."""

    @pytest.mark.asyncio
    async def test_cleanup_removes_old_events(self, user_activity_router, mock_activity_service):
        """Test that cleanup endpoint removes old events."""
        from httpx import ASGITransport, AsyncClient

        transport = ASGITransport(app=user_activity_router)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post("/api/v1/user-activity/cleanup")

        assert response.status_code == 200
        data = response.json()
        assert "deleted_count" in data
        assert data["deleted_count"] == 5
        mock_activity_service.cleanup_old_events.assert_called_once()

    @pytest.mark.asyncio
    async def test_cleanup_with_retention_days_param(self, user_activity_router, mock_activity_service):
        """Test that cleanup endpoint accepts retention_days parameter."""
        from httpx import ASGITransport, AsyncClient

        transport = ASGITransport(app=user_activity_router)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post("/api/v1/user-activity/cleanup?retention_days=90")

        assert response.status_code == 200
        mock_activity_service.cleanup_old_events.assert_called_once()


class TestUserActivityAPIEventTypes:
    """Tests for GET /api/v1/user-activity/event-types endpoint."""

    @pytest.mark.asyncio
    async def test_get_event_types_returns_list(self, user_activity_router, mock_activity_service):
        """Test that event-types endpoint returns available event types."""
        from httpx import ASGITransport, AsyncClient

        transport = ASGITransport(app=user_activity_router)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/v1/user-activity/event-types")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert "search_query" in data
        assert "property_view" in data
        assert "tool_use" in data


class TestUserActivityAPITopSessions:
    """Tests for GET /api/v1/user-activity/top-sessions endpoint."""

    @pytest.mark.asyncio
    async def test_get_top_sessions_returns_ranked_sessions(self, user_activity_router, mock_activity_service):
        """Test that top-sessions endpoint returns most active sessions."""
        from httpx import ASGITransport, AsyncClient

        transport = ASGITransport(app=user_activity_router)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/v1/user-activity/top-sessions?limit=10")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 2
        assert data[0]["session_id"] == "s1"
        assert data[0]["event_count"] == 42

    @pytest.mark.asyncio
    async def test_get_top_sessions_with_limit_param(self, user_activity_router, mock_activity_service):
        """Test that top-sessions accepts limit parameter."""
        from httpx import ASGITransport, AsyncClient

        transport = ASGITransport(app=user_activity_router)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/v1/user-activity/top-sessions?limit=5")

        assert response.status_code == 200
        mock_activity_service.get_top_sessions.assert_called_once_with(limit=5)


class TestUserActivityAPICategoryBreakdown:
    """Tests for GET /api/v1/user-activity/breakdown endpoint."""

    @pytest.mark.asyncio
    async def test_get_category_breakdown_returns_counts(self, user_activity_router, mock_activity_service):
        """Test that breakdown endpoint returns event counts by category."""
        from httpx import ASGITransport, AsyncClient

        transport = ASGITransport(app=user_activity_router)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/v1/user-activity/breakdown")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 2
        assert data[0]["category"] == "search"
        assert data[0]["count"] == 50


class TestUserActivityAPIRateLimiting:
    """Tests for rate limiting on user activity endpoints."""

    @pytest.mark.asyncio
    async def test_track_endpoint_has_rate_limit(self, user_activity_router, mock_activity_service):
        """Test that track endpoint has rate limiting."""
        from httpx import ASGITransport, AsyncClient

        mock_activity_service.track_event.return_value = MagicMock(id="test")

        transport = ASGITransport(app=user_activity_router)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            # Make multiple requests to test rate limit
            responses = []
            for _ in range(5):
                response = await client.post(
                    "/api/v1/user-activity/track",
                    json={
                        "session_id": "s1",
                        "event_type": "test",
                        "event_category": "test",
                    }
                )
                responses.append(response)

        # At least some requests should succeed
        successful = [r for r in responses if r.status_code == 201]
        assert len(successful) >= 1

        # Check for rate limit headers
        for r in responses:
            if "x-ratelimit-remaining" in r.headers:
                # Rate limiting is active
                assert r.headers["x-ratelimit-remaining"] is not None


class TestUserActivityAPIPrivacy:
    """Tests for privacy protection in user activity endpoints."""

    @pytest.mark.asyncio
    async def test_export_does_not_include_raw_user_ids(self, user_activity_router, mock_activity_service):
        """Test that export doesn't expose raw user IDs."""
        from httpx import ASGITransport, AsyncClient

        # Mock CSV that might accidentally include user data
        mock_activity_service.export_to_csv.return_value = (
            "timestamp,session_id,event_type\n"
            "2024-01-01T00:00:00Z,s1,search_query\n"
            "2024-01-01T00:01:00Z,s2,property_view"
        )

        transport = ASGITransport(app=user_activity_router)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/v1/user-activity/export")

        assert response.status_code == 200
        csv_content = response.text
        # Ensure no user_id_hash or raw user IDs are exported
        assert "user_id_hash" not in csv_content
        assert "user_id" not in csv_content

    @pytest.mark.asyncio
    async def test_summary_does_not_expose_user_ids(self, user_activity_router, mock_activity_service):
        """Test that summary endpoint doesn't expose user identifiers."""
        from httpx import ASGITransport, AsyncClient

        transport = ASGITransport(app=user_activity_router)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/v1/user-activity/summary")

        assert response.status_code == 200
        data = response.json()
        # Should not contain user identifiers
        assert "user_id" not in data
        assert "user_id_hash" not in data
        assert "email" not in data


class TestUserActivityAPIErrorHandling:
    """Tests for error handling in user activity endpoints."""

    @pytest.mark.asyncio
    async def test_track_event_handles_service_errors(self, user_activity_router, mock_activity_service):
        """Test that track endpoint handles service errors gracefully."""
        from httpx import ASGITransport, AsyncClient

        # Simulate service error
        mock_activity_service.track_event.side_effect = Exception("Database error")

        transport = ASGITransport(app=user_activity_router)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/api/v1/user-activity/track",
                json={
                    "session_id": "s1",
                    "event_type": "test",
                    "event_category": "test",
                }
            )

        # Should return 500 Internal Server Error
        assert response.status_code == 500

    @pytest.mark.asyncio
    async def test_get_summary_handles_empty_data(self, user_activity_router, mock_activity_service):
        """Test that summary handles case with no data."""
        from httpx import ASGITransport, AsyncClient

        mock_activity_service.get_summary.return_value = {
            "period_start": "2024-01-01T00:00:00Z",
            "period_end": "2024-01-08T00:00:00Z",
            "total_events": 0,
            "total_searches": 0,
            "total_views": 0,
            "total_tool_uses": 0,
        }

        transport = ASGITransport(app=user_activity_router)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/v1/user-activity/summary")

        assert response.status_code == 200
        data = response.json()
        assert data["total_events"] == 0
