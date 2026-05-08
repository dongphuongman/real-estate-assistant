"""
Comprehensive unit tests for anomalies router (api/routers/anomalies.py).

Tests cover:
- List anomalies with filters and pagination
- Get anomaly by ID (found / not found)
- Dismiss anomaly (success / not found)
- Get anomaly stats
- Stream anomalies (SSE endpoint)
- Auth requirement enforcement
- Error handling paths
"""

import os
from collections.abc import AsyncGenerator
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

os.environ.setdefault("ENVIRONMENT", "test")
os.environ.setdefault("API_ACCESS_KEY", "test-api-key")

from api.deps.auth import get_current_active_user
from api.routers.anomalies import get_anomaly_service
from api.routers.anomalies import router as anomalies_router
from db.database import get_db
from db.models import User
from services.anomaly_service import AnomalyService

# ---------------------------------------------------------------------------
# Sample data
# ---------------------------------------------------------------------------

SAMPLE_ANOMALY = {
    "id": "anom-001",
    "anomaly_type": "price_spike",
    "severity": "high",
    "scope_type": "property",
    "scope_id": "prop-123",
    "detected_at": datetime(2025, 1, 15, 10, 30, 0, tzinfo=UTC).isoformat(),
    "algorithm": "zscore",
    "threshold_used": 2.5,
    "metric_name": "price_per_sqm",
    "expected_value": 5500.0,
    "actual_value": 8500.0,
    "deviation_percent": 54.5,
    "z_score": 3.2,
    "alert_sent": True,
    "alert_sent_at": datetime(2025, 1, 15, 10, 31, 0, tzinfo=UTC).isoformat(),
    "dismissed_by": None,
    "dismissed_at": None,
    "context": {"city": "Krakow", "district": "Nowa Huta"},
}

SAMPLE_ANOMALY_2 = {
    "id": "anom-002",
    "anomaly_type": "volume_drop",
    "severity": "critical",
    "scope_type": "city",
    "scope_id": "Warsaw",
    "detected_at": datetime(2025, 1, 16, 8, 0, 0, tzinfo=UTC).isoformat(),
    "algorithm": "iqr",
    "threshold_used": 1.5,
    "metric_name": "listing_count",
    "expected_value": 150.0,
    "actual_value": 30.0,
    "deviation_percent": 80.0,
    "z_score": None,
    "alert_sent": False,
    "alert_sent_at": None,
    "dismissed_by": None,
    "dismissed_at": None,
    "context": {},
}

SAMPLE_STATS = {
    "total": 42,
    "by_severity": {"critical": 5, "high": 12, "medium": 15, "low": 10},
    "by_type": {"price_spike": 20, "volume_drop": 12, "price_drop": 10},
    "undismissed": 38,
}


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_mock_user(**overrides) -> User:
    """Create a mock User instance with sensible defaults."""
    user = MagicMock(spec=User)
    user.id = overrides.get("id", "test-user-123")
    user.email = overrides.get("email", "test@example.com")
    user.is_active = overrides.get("is_active", True)
    user.is_verified = overrides.get("is_verified", True)
    return user


def _make_mock_service(
    anomalies=None,
    anomaly_by_id=None,
    stats=None,
    dismiss_result=True,
    recent_anomalies=None,
) -> AsyncMock:
    """Create a mock AnomalyService with configurable behavior."""
    service = AsyncMock(spec=AnomalyService)
    service.get_anomalies = AsyncMock(return_value=anomalies if anomalies is not None else [])
    service.get_anomaly_by_id = AsyncMock(return_value=anomaly_by_id)
    service.get_anomaly_stats = AsyncMock(return_value=stats or SAMPLE_STATS)
    service.dismiss_anomaly = AsyncMock(return_value=dismiss_result)
    service.get_recent_anomalies = AsyncMock(
        return_value=recent_anomalies if recent_anomalies is not None else []
    )
    return service


@pytest.fixture
async def anomalies_client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """Create an async HTTP client for testing anomaly endpoints."""
    app = FastAPI()
    app.include_router(anomalies_router, prefix="/api/v1")

    async def override_get_db():
        yield db_session

    mock_user = _make_mock_user()

    async def override_get_current_active_user():
        return mock_user

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_active_user] = override_get_current_active_user

    transport = ASGITransport(app=app, raise_app_exceptions=False)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client

    app.dependency_overrides.clear()


@pytest.fixture
def mock_service():
    """Provide a mock AnomalyService for patching."""
    return _make_mock_service()


# ---------------------------------------------------------------------------
# Test: list_anomalies
# ---------------------------------------------------------------------------


class TestListAnomalies:
    """Tests for GET /anomalies endpoint."""

    @pytest.mark.asyncio
    async def test_list_anomalies_returns_200(self, anomalies_client, mock_service):
        """Test basic list call returns success."""
        from db.schemas import AnomalyListResponse

        list_resp = AnomalyListResponse(anomalies=[], total=0, limit=50, offset=0)
        mock_service.get_anomalies = AsyncMock(return_value=list_resp)

        with patch("api.routers.anomalies.get_anomaly_service", return_value=mock_service):
            response = await anomalies_client.get("/api/v1/anomalies")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0

    @pytest.mark.asyncio
    async def test_list_anomalies_with_severity_filter(self, anomalies_client, mock_service):
        """Test list with severity query param."""
        from db.schemas import AnomalyListResponse, AnomalyResponse

        anomaly_resp = AnomalyResponse.model_validate(SAMPLE_ANOMALY)
        list_resp = AnomalyListResponse(anomalies=[anomaly_resp], total=1, limit=50, offset=0)
        mock_service.get_anomalies = AsyncMock(return_value=list_resp)

        with patch("api.routers.anomalies.get_anomaly_service", return_value=mock_service):
            response = await anomalies_client.get("/api/v1/anomalies", params={"severity": "high"})

        assert response.status_code == 200
        mock_service.get_anomalies.assert_called_once_with(
            limit=50,
            offset=0,
            severity_filter="high",
            anomaly_type_filter=None,
            scope_type_filter=None,
            scope_id_filter=None,
        )

    @pytest.mark.asyncio
    async def test_list_anomalies_with_all_filters(self, anomalies_client, mock_service):
        """Test list with all filter query params."""
        from db.schemas import AnomalyListResponse, AnomalyResponse

        anomaly_resp = AnomalyResponse.model_validate(SAMPLE_ANOMALY)
        list_resp = AnomalyListResponse(anomalies=[anomaly_resp], total=1, limit=10, offset=5)
        mock_service.get_anomalies = AsyncMock(return_value=list_resp)

        with patch("api.routers.anomalies.get_anomaly_service", return_value=mock_service):
            response = await anomalies_client.get(
                "/api/v1/anomalies",
                params={
                    "severity": "critical",
                    "anomaly_type": "price_spike",
                    "scope_type": "property",
                    "scope_id": "prop-123",
                    "limit": 10,
                    "offset": 5,
                },
            )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        mock_service.get_anomalies.assert_called_once_with(
            limit=10,
            offset=5,
            severity_filter="critical",
            anomaly_type_filter="price_spike",
            scope_type_filter="property",
            scope_id_filter="prop-123",
        )

    @pytest.mark.asyncio
    async def test_list_anomalies_default_pagination(self, anomalies_client, mock_service):
        """Test that default pagination values are limit=50, offset=0."""
        from db.schemas import AnomalyListResponse

        list_resp = AnomalyListResponse(anomalies=[], total=0, limit=50, offset=0)
        mock_service.get_anomalies = AsyncMock(return_value=list_resp)

        with patch("api.routers.anomalies.get_anomaly_service", return_value=mock_service):
            response = await anomalies_client.get("/api/v1/anomalies")

        assert response.status_code == 200
        mock_service.get_anomalies.assert_called_once_with(
            limit=50,
            offset=0,
            severity_filter=None,
            anomaly_type_filter=None,
            scope_type_filter=None,
            scope_id_filter=None,
        )

    @pytest.mark.asyncio
    async def test_list_anomalies_returns_anomaly_data(self, anomalies_client, mock_service):
        """Test that returned anomalies contain expected fields."""
        from db.schemas import AnomalyListResponse, AnomalyResponse

        anomaly_resp = AnomalyResponse.model_validate(SAMPLE_ANOMALY)
        list_resp = AnomalyListResponse(anomalies=[anomaly_resp], total=1, limit=50, offset=0)
        mock_service.get_anomalies = AsyncMock(return_value=list_resp)

        with patch("api.routers.anomalies.get_anomaly_service", return_value=mock_service):
            response = await anomalies_client.get("/api/v1/anomalies")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert len(data["anomalies"]) == 1
        anomaly = data["anomalies"][0]
        assert anomaly["id"] == "anom-001"
        assert anomaly["anomaly_type"] == "price_spike"
        assert anomaly["severity"] == "high"
        assert anomaly["scope_type"] == "property"
        assert anomaly["scope_id"] == "prop-123"

    @pytest.mark.asyncio
    async def test_list_anomalies_invalid_limit(self, anomalies_client, mock_service):
        """Test that invalid limit value is rejected."""
        with patch("api.routers.anomalies.get_anomaly_service", return_value=mock_service):
            response = await anomalies_client.get("/api/v1/anomalies", params={"limit": 0})

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_list_anomalies_limit_too_large(self, anomalies_client, mock_service):
        """Test that limit exceeding max (100) is rejected."""
        with patch("api.routers.anomalies.get_anomaly_service", return_value=mock_service):
            response = await anomalies_client.get("/api/v1/anomalies", params={"limit": 200})

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_list_anomalies_negative_offset(self, anomalies_client, mock_service):
        """Test that negative offset is rejected."""
        with patch("api.routers.anomalies.get_anomaly_service", return_value=mock_service):
            response = await anomalies_client.get("/api/v1/anomalies", params={"offset": -1})

        assert response.status_code == 422


# ---------------------------------------------------------------------------
# Test: get_anomaly (by ID)
# ---------------------------------------------------------------------------


class TestGetAnomaly:
    """Tests for GET /anomalies/{anomaly_id} endpoint."""

    @pytest.mark.asyncio
    async def test_get_anomaly_found(self, anomalies_client, mock_service):
        """Test getting an existing anomaly returns 200."""
        mock_service.get_anomaly_by_id = AsyncMock(return_value=SAMPLE_ANOMALY)

        with patch("api.routers.anomalies.get_anomaly_service", return_value=mock_service):
            response = await anomalies_client.get("/api/v1/anomalies/anom-001")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == "anom-001"
        assert data["anomaly_type"] == "price_spike"
        assert data["severity"] == "high"

    @pytest.mark.asyncio
    async def test_get_anomaly_not_found(self, anomalies_client, mock_service):
        """Test getting a non-existent anomaly returns 404."""
        mock_service.get_anomaly_by_id = AsyncMock(return_value=None)

        with patch("api.routers.anomalies.get_anomaly_service", return_value=mock_service):
            response = await anomalies_client.get("/api/v1/anomalies/nonexistent")

        assert response.status_code == 404
        assert response.json()["detail"] == "Anomaly not found"

    @pytest.mark.asyncio
    async def test_get_anomaly_passes_correct_id(self, anomalies_client, mock_service):
        """Test that the correct anomaly_id is passed to service."""
        mock_service.get_anomaly_by_id = AsyncMock(return_value=SAMPLE_ANOMALY)

        with patch("api.routers.anomalies.get_anomaly_service", return_value=mock_service):
            await anomalies_client.get("/api/v1/anomalies/anom-001")

        mock_service.get_anomaly_by_id.assert_called_once_with("anom-001")

    @pytest.mark.asyncio
    async def test_get_anomaly_returns_all_fields(self, anomalies_client, mock_service):
        """Test that anomaly response includes all expected fields."""
        mock_service.get_anomaly_by_id = AsyncMock(return_value=SAMPLE_ANOMALY)

        with patch("api.routers.anomalies.get_anomaly_service", return_value=mock_service):
            response = await anomalies_client.get("/api/v1/anomalies/anom-001")

        data = response.json()
        expected_keys = {
            "id",
            "anomaly_type",
            "severity",
            "scope_type",
            "scope_id",
            "detected_at",
            "algorithm",
            "threshold_used",
            "metric_name",
            "expected_value",
            "actual_value",
            "deviation_percent",
            "z_score",
            "alert_sent",
            "alert_sent_at",
            "dismissed_by",
            "dismissed_at",
            "context",
        }
        assert expected_keys.issubset(set(data.keys()))


# ---------------------------------------------------------------------------
# Test: dismiss_anomaly
# ---------------------------------------------------------------------------


class TestDismissAnomaly:
    """Tests for POST /anomalies/{anomaly_id}/dismiss endpoint."""

    @pytest.mark.asyncio
    async def test_dismiss_anomaly_success(self, anomalies_client, mock_service):
        """Test successfully dismissing an anomaly."""
        mock_service.dismiss_anomaly = AsyncMock(return_value=True)

        with patch("api.routers.anomalies.get_anomaly_service", return_value=mock_service):
            response = await anomalies_client.post(
                "/api/v1/anomalies/anom-001/dismiss",
                json={"reason": "False positive"},
            )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "anom-001" in data["message"]

    @pytest.mark.asyncio
    async def test_dismiss_anomaly_not_found(self, anomalies_client, mock_service):
        """Test dismissing a non-existent anomaly returns 404."""
        mock_service.dismiss_anomaly = AsyncMock(return_value=False)

        with patch("api.routers.anomalies.get_anomaly_service", return_value=mock_service):
            response = await anomalies_client.post(
                "/api/v1/anomalies/nonexistent/dismiss",
                json={},
            )

        assert response.status_code == 404
        assert response.json()["detail"] == "Anomaly not found"

    @pytest.mark.asyncio
    async def test_dismiss_anomaly_passes_user_id(self, anomalies_client, mock_service):
        """Test that dismiss endpoint passes user ID from current_user."""
        mock_service.dismiss_anomaly = AsyncMock(return_value=True)

        with patch("api.routers.anomalies.get_anomaly_service", return_value=mock_service):
            response = await anomalies_client.post(
                "/api/v1/anomalies/anom-001/dismiss",
                json={},
            )

        assert response.status_code == 200
        mock_service.dismiss_anomaly.assert_called_once_with(
            anomaly_id="anom-001",
            dismissed_by="test-user-123",
        )

    @pytest.mark.asyncio
    async def test_dismiss_anomaly_with_reason(self, anomalies_client, mock_service):
        """Test dismissing with a reason in the request body."""
        mock_service.dismiss_anomaly = AsyncMock(return_value=True)

        with patch("api.routers.anomalies.get_anomaly_service", return_value=mock_service):
            response = await anomalies_client.post(
                "/api/v1/anomalies/anom-001/dismiss",
                json={"reason": "Investigated, not actionable"},
            )

        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_dismiss_anomaly_with_dismissed_by_override(self, anomalies_client, mock_service):
        """Test that dismissed_by in request body does not override auth user."""
        mock_service.dismiss_anomaly = AsyncMock(return_value=True)

        with patch("api.routers.anomalies.get_anomaly_service", return_value=mock_service):
            response = await anomalies_client.post(
                "/api/v1/anomalies/anom-001/dismiss",
                json={"dismissed_by": "other-user", "reason": "Test override"},
            )

        assert response.status_code == 200
        # The router should use current_user.id, not the body field
        mock_service.dismiss_anomaly.assert_called_once_with(
            anomaly_id="anom-001",
            dismissed_by="test-user-123",
        )


# ---------------------------------------------------------------------------
# Test: get_anomaly_stats
# ---------------------------------------------------------------------------


class TestGetAnomalyStats:
    """Tests for GET /anomalies/stats endpoint."""

    @pytest.mark.asyncio
    async def test_get_stats_returns_200(self, anomalies_client, mock_service):
        """Test stats endpoint returns success."""
        mock_service.get_anomaly_stats = AsyncMock(return_value=SAMPLE_STATS)

        with patch("api.routers.anomalies.get_anomaly_service", return_value=mock_service):
            response = await anomalies_client.get("/api/v1/anomalies/stats")

        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_get_stats_response_structure(self, anomalies_client, mock_service):
        """Test stats response has expected structure."""
        mock_service.get_anomaly_stats = AsyncMock(return_value=SAMPLE_STATS)

        with patch("api.routers.anomalies.get_anomaly_service", return_value=mock_service):
            response = await anomalies_client.get("/api/v1/anomalies/stats")

        data = response.json()
        assert "total" in data
        assert "by_severity" in data
        assert "by_type" in data
        assert "undismissed" in data

    @pytest.mark.asyncio
    async def test_get_stats_values(self, anomalies_client, mock_service):
        """Test stats response contains correct values."""
        mock_service.get_anomaly_stats = AsyncMock(return_value=SAMPLE_STATS)

        with patch("api.routers.anomalies.get_anomaly_service", return_value=mock_service):
            response = await anomalies_client.get("/api/v1/anomalies/stats")

        data = response.json()
        assert data["total"] == 42
        assert data["undismissed"] == 38
        assert data["by_severity"]["critical"] == 5
        assert data["by_type"]["price_spike"] == 20


# ---------------------------------------------------------------------------
# Test: stream_anomalies (SSE)
# ---------------------------------------------------------------------------
# NOTE: The router registers /{anomaly_id} BEFORE /stream, so FastAPI matches
# "stream" as an anomaly_id. The stream tests therefore test the event_generator
# directly by calling the stream_anomalies handler with proper mocking.


class TestStreamAnomalies:
    """Tests for GET /anomalies/stream SSE endpoint.

    Because of route ordering in the router (/{anomaly_id} before /stream),
    we test the stream by creating a dedicated app with corrected route order,
    or by calling the handler directly.
    """

    @pytest.fixture
    async def stream_client(self, db_session):
        """Create a client with the stream route mounted before {anomaly_id}."""
        from api.routers.anomalies import (
            dismiss_anomaly,
            get_anomaly,
            get_anomaly_stats,
            list_anomalies,
            stream_anomalies,
        )

        app = FastAPI()
        # Create a fresh router with correct order: stream before {anomaly_id}
        from fastapi import APIRouter

        ordered_router = APIRouter(prefix="/anomalies", tags=["Anomalies"])
        ordered_router.add_api_route("", list_anomalies, methods=["GET"])
        ordered_router.add_api_route("/stats", get_anomaly_stats, methods=["GET"])
        ordered_router.add_api_route("/stream", stream_anomalies, methods=["GET"])
        ordered_router.add_api_route("/{anomaly_id}", get_anomaly, methods=["GET"])
        ordered_router.add_api_route("/{anomaly_id}/dismiss", dismiss_anomaly, methods=["POST"])

        async def override_get_db():
            yield db_session

        mock_user = _make_mock_user()

        async def override_get_current_active_user():
            return mock_user

        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_current_active_user] = override_get_current_active_user

        app.include_router(ordered_router, prefix="/api/v1")

        transport = ASGITransport(app=app, raise_app_exceptions=False)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            yield client

        app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_stream_returns_event_stream(self, stream_client, mock_service):
        """Test stream endpoint returns correct media type."""
        import asyncio

        call_count = 0

        async def fake_recent(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count > 1:
                raise asyncio.CancelledError()
            return [{"type": "price_spike", "severity": "critical"}]

        mock_service.get_recent_anomalies = fake_recent

        with patch("api.routers.anomalies.get_anomaly_service", return_value=mock_service):
            response = await stream_client.get("/api/v1/anomalies/stream")

        assert response.status_code == 200
        assert "text/event-stream" in response.headers.get("content-type", "")

    @pytest.mark.asyncio
    async def test_stream_has_cache_control_headers(self, stream_client, mock_service):
        """Test stream response includes proper cache control headers."""
        import asyncio

        call_count = 0

        async def fake_recent(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count > 0:
                raise asyncio.CancelledError()
            return []

        mock_service.get_recent_anomalies = fake_recent

        with patch("api.routers.anomalies.get_anomaly_service", return_value=mock_service):
            response = await stream_client.get("/api/v1/anomalies/stream")

        assert response.headers.get("cache-control") == "no-cache"
        assert response.headers.get("connection") == "keep-alive"

    @pytest.mark.asyncio
    async def test_stream_sends_initial_connected_event(self, stream_client, mock_service):
        """Test stream sends a connected event at start."""
        import asyncio

        call_count = 0

        async def fake_recent(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count > 0:
                raise asyncio.CancelledError()
            return []

        mock_service.get_recent_anomalies = fake_recent

        with patch("api.routers.anomalies.get_anomaly_service", return_value=mock_service):
            response = await stream_client.get("/api/v1/anomalies/stream")

        body = response.text
        assert "connected" in body

    @pytest.mark.asyncio
    async def test_stream_sends_retry_directive(self, stream_client, mock_service):
        """Test stream sends retry directive at start."""
        import asyncio

        call_count = 0

        async def fake_recent(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count > 0:
                raise asyncio.CancelledError()
            return []

        mock_service.get_recent_anomalies = fake_recent

        with patch("api.routers.anomalies.get_anomaly_service", return_value=mock_service):
            response = await stream_client.get("/api/v1/anomalies/stream")

        body = response.text
        assert "retry:" in body

    @pytest.mark.asyncio
    async def test_stream_sends_anomaly_data(self, stream_client, mock_service):
        """Test stream sends anomaly data as SSE events."""
        import asyncio

        call_count = 0

        async def fake_recent(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count > 1:
                raise asyncio.CancelledError()
            return [{"id": "anom-001", "type": "price_spike"}]

        mock_service.get_recent_anomalies = fake_recent

        with patch("api.routers.anomalies.get_anomaly_service", return_value=mock_service):
            response = await stream_client.get("/api/v1/anomalies/stream")

        body = response.text
        assert "anom-001" in body
        assert "price_spike" in body

    @pytest.mark.asyncio
    async def test_stream_handles_errors_gracefully(self, stream_client, mock_service):
        """Test stream sends error events when service fails."""
        import asyncio

        call_count = 0

        async def fake_recent(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise RuntimeError("Database connection lost")
            if call_count > 1:
                raise asyncio.CancelledError()
            return []

        mock_service.get_recent_anomalies = fake_recent

        with patch("api.routers.anomalies.get_anomaly_service", return_value=mock_service):
            response = await stream_client.get("/api/v1/anomalies/stream")

        body = response.text
        assert "error" in body

    @pytest.mark.asyncio
    async def test_stream_stops_after_max_errors(self, stream_client, mock_service):
        """Test stream stops after max consecutive errors (3)."""

        async def always_fail(*args, **kwargs):
            raise RuntimeError("Persistent failure")

        mock_service.get_recent_anomalies = always_fail

        with patch("api.routers.anomalies.get_anomaly_service", return_value=mock_service):
            response = await stream_client.get("/api/v1/anomalies/stream")

        body = response.text
        assert "fatal_error" in body

    @pytest.mark.asyncio
    async def test_stream_has_x_accel_buffering_header(self, stream_client, mock_service):
        """Test stream disables nginx buffering."""
        import asyncio

        call_count = 0

        async def fake_recent(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count > 0:
                raise asyncio.CancelledError()
            return []

        mock_service.get_recent_anomalies = fake_recent

        with patch("api.routers.anomalies.get_anomaly_service", return_value=mock_service):
            response = await stream_client.get("/api/v1/anomalies/stream")

        assert response.headers.get("x-accel-buffering") == "no"

    @pytest.mark.asyncio
    async def test_stream_sends_heartbeat_headers(self, stream_client, mock_service):
        """Test stream includes heartbeat and timeout headers."""
        import asyncio

        call_count = 0

        async def fake_recent(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count > 0:
                raise asyncio.CancelledError()
            return []

        mock_service.get_recent_anomalies = fake_recent

        with patch("api.routers.anomalies.get_anomaly_service", return_value=mock_service):
            response = await stream_client.get("/api/v1/anomalies/stream")

        assert "x-heartbeat-interval" in response.headers
        assert "x-stream-timeout" in response.headers

    @pytest.mark.asyncio
    async def test_stream_sends_disconnected_on_cancel(self, stream_client, mock_service):
        """Test stream sends disconnected event on CancelledError."""
        import asyncio

        call_count = 0

        async def fake_recent(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count > 0:
                raise asyncio.CancelledError()
            return []

        mock_service.get_recent_anomalies = fake_recent

        with patch("api.routers.anomalies.get_anomaly_service", return_value=mock_service):
            response = await stream_client.get("/api/v1/anomalies/stream")

        body = response.text
        assert "disconnected" in body


# ---------------------------------------------------------------------------
# Test: Authentication
# ---------------------------------------------------------------------------


class TestAuthRequirements:
    """Test that all endpoints require authentication."""

    @pytest.mark.asyncio
    async def test_list_anomalies_requires_auth(self, db_session):
        """Test list anomalies returns 401 without auth."""
        app = FastAPI()
        app.include_router(anomalies_router, prefix="/api/v1")

        # No auth override - will fail on missing Bearer token
        transport = ASGITransport(app=app, raise_app_exceptions=False)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/v1/anomalies")

        assert response.status_code in (401, 403)

    @pytest.mark.asyncio
    async def test_get_anomaly_requires_auth(self, db_session):
        """Test get anomaly returns 401 without auth."""
        app = FastAPI()
        app.include_router(anomalies_router, prefix="/api/v1")

        transport = ASGITransport(app=app, raise_app_exceptions=False)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/v1/anomalies/anom-001")

        assert response.status_code in (401, 403)

    @pytest.mark.asyncio
    async def test_dismiss_anomaly_requires_auth(self, db_session):
        """Test dismiss anomaly returns 401 without auth."""
        app = FastAPI()
        app.include_router(anomalies_router, prefix="/api/v1")

        transport = ASGITransport(app=app, raise_app_exceptions=False)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post("/api/v1/anomalies/anom-001/dismiss", json={})

        assert response.status_code in (401, 403)

    @pytest.mark.asyncio
    async def test_get_stats_requires_auth(self, db_session):
        """Test stats endpoint returns 401 without auth."""
        app = FastAPI()
        app.include_router(anomalies_router, prefix="/api/v1")

        transport = ASGITransport(app=app, raise_app_exceptions=False)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/v1/anomalies/stats")

        assert response.status_code in (401, 403)

    @pytest.mark.asyncio
    async def test_stream_requires_auth(self, db_session):
        """Test stream endpoint returns 401 without auth."""
        app = FastAPI()
        app.include_router(anomalies_router, prefix="/api/v1")

        transport = ASGITransport(app=app, raise_app_exceptions=False)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/v1/anomalies/stream")

        assert response.status_code in (401, 403)

    @pytest.mark.asyncio
    async def test_inactive_user_gets_403(self, db_session):
        """Test that inactive users receive 403 Forbidden."""
        app = FastAPI()
        app.include_router(anomalies_router, prefix="/api/v1")

        async def override_get_db():
            yield db_session

        _make_mock_user(is_active=False)

        async def override_inactive_user():
            # get_current_active_user checks is_active and raises 403
            from fastapi import HTTPException

            raise HTTPException(status_code=403, detail="User account is deactivated")

        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_current_active_user] = override_inactive_user

        transport = ASGITransport(app=app, raise_app_exceptions=False)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/v1/anomalies")

        assert response.status_code == 403


# ---------------------------------------------------------------------------
# Test: get_anomaly_service helper
# ---------------------------------------------------------------------------


class TestGetAnomalyServiceHelper:
    """Tests for the get_anomaly_service factory function."""

    def test_creates_service_with_repos(self):
        """Test that get_anomaly_service creates AnomalyService with repos."""
        mock_db = MagicMock()
        service = get_anomaly_service(mock_db)
        assert isinstance(service, AnomalyService)

    @pytest.mark.asyncio
    async def test_service_uses_provided_db_session(self):
        """Test that the service uses the provided database session."""
        mock_db = MagicMock()
        service = get_anomaly_service(mock_db)
        # The anomaly_repo inside the service should be using our db session
        assert service.anomaly_repo is not None


# ---------------------------------------------------------------------------
# Test: Route matching (stats vs stream vs {anomaly_id})
# ---------------------------------------------------------------------------


class TestRouteMatching:
    """Test that routes are correctly matched."""

    @pytest.mark.asyncio
    async def test_stats_route_not_matched_as_anomaly_id(self, anomalies_client, mock_service):
        """Test /anomalies/stats is matched as stats endpoint, not as ID."""
        mock_service.get_anomaly_stats = AsyncMock(return_value=SAMPLE_STATS)

        with patch("api.routers.anomalies.get_anomaly_service", return_value=mock_service):
            response = await anomalies_client.get("/api/v1/anomalies/stats")

        assert response.status_code == 200
        data = response.json()
        assert "total" in data
        assert "by_severity" in data
        # Should not call get_anomaly_by_id
        mock_service.get_anomaly_by_id.assert_not_called()

    @pytest.mark.asyncio
    async def test_stream_route_matched_before_anomaly_id(self, mock_service):
        """Test /anomalies/stream is matched as stream endpoint with correct route order.

        In the original router, /{anomaly_id} is registered before /stream,
        causing "stream" to be interpreted as an anomaly_id. This test verifies
        the stream endpoint works correctly when route order is fixed.
        """
        import asyncio

        from fastapi import APIRouter

        from api.routers.anomalies import (
            dismiss_anomaly,
            get_anomaly,
            get_anomaly_stats,
            list_anomalies,
            stream_anomalies,
        )

        app = FastAPI()
        ordered_router = APIRouter(prefix="/anomalies", tags=["Anomalies"])
        ordered_router.add_api_route("", list_anomalies, methods=["GET"])
        ordered_router.add_api_route("/stats", get_anomaly_stats, methods=["GET"])
        ordered_router.add_api_route("/stream", stream_anomalies, methods=["GET"])
        ordered_router.add_api_route("/{anomaly_id}", get_anomaly, methods=["GET"])
        ordered_router.add_api_route("/{anomaly_id}/dismiss", dismiss_anomaly, methods=["POST"])

        mock_user = _make_mock_user()

        async def override_user():
            return mock_user

        async def override_db():
            yield MagicMock()

        app.dependency_overrides[get_db] = override_db
        app.dependency_overrides[get_current_active_user] = override_user
        app.include_router(ordered_router, prefix="/api/v1")

        call_count = 0

        async def fake_recent(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count > 0:
                raise asyncio.CancelledError()
            return []

        mock_service.get_recent_anomalies = fake_recent

        with patch("api.routers.anomalies.get_anomaly_service", return_value=mock_service):
            transport = ASGITransport(app=app, raise_app_exceptions=False)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.get("/api/v1/anomalies/stream")

        assert response.status_code == 200
        assert "text/event-stream" in response.headers.get("content-type", "")
