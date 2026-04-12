"""Integration tests for esignatures router."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from api.deps.auth import get_current_active_user
from api.routers import esignatures
from db.database import get_db
from db.schemas import UserResponse


def _make_signature_request_mock(**overrides):
    """Create a mock signature request with all required fields."""
    m = MagicMock()
    m.id = overrides.get("id", "sig-001")
    m.user_id = overrides.get("user_id", "test-user-123")
    m.title = overrides.get("title", "Purchase Agreement")
    m.provider = overrides.get("provider", "hellosign")
    m.document_id = overrides.get("document_id", "doc-001")
    m.template_id = overrides.get("template_id", None)
    m.property_id = overrides.get("property_id", None)
    m.subject = overrides.get("subject", "Please sign")
    m.message = overrides.get("message", "Kindly review and sign")
    m.status = overrides.get("status", "sent")
    m.signers = overrides.get(
        "signers",
        [
            {
                "email": "buyer@example.com",
                "name": "John Buyer",
                "role": "buyer",
                "order": 1,
                "status": "pending",
                "signed_at": None,
            }
        ],
    )
    m.provider_envelope_id = overrides.get("provider_envelope_id", "env-001")
    m.document_content_hash = overrides.get("document_content_hash", "abc123")
    m.expires_at = overrides.get("expires_at", None)
    m.sent_at = overrides.get("sent_at", datetime(2025, 6, 1, tzinfo=timezone.utc))
    m.completed_at = overrides.get("completed_at", None)
    m.reminder_count = overrides.get("reminder_count", 0)
    m.variables = overrides.get("variables", None)
    m.created_at = overrides.get("created_at", datetime(2025, 1, 1, tzinfo=timezone.utc))
    m.updated_at = overrides.get("updated_at", datetime(2025, 1, 2, tzinfo=timezone.utc))
    return m


@pytest.fixture
def test_app(db_session):
    """Create test app with esignatures router and mocked dependencies."""
    app = FastAPI()
    app.include_router(esignatures.router, prefix="/api/v1")

    async def override_get_db():
        yield db_session

    async def override_get_current_user():
        return UserResponse(
            id="test-user-123",
            email="test@example.com",
            roles=["user"],
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


class TestEsignaturesAPI:
    """Integration tests for esignatures endpoints."""

    @pytest.mark.asyncio
    async def test_list_signature_requests_empty(self, client):
        """Returns empty list when no signature requests exist."""
        mock_repo = AsyncMock()
        mock_repo.get_by_user.return_value = []
        mock_repo.count_by_user.return_value = 0

        with patch(
            "api.routers.esignatures.SignatureRequestRepository",
            return_value=mock_repo,
        ):
            resp = await client.get("/api/v1/signatures")
        assert resp.status_code == 200
        data = resp.json()
        assert data["items"] == []
        assert data["total"] == 0

    @pytest.mark.asyncio
    async def test_get_signature_request_not_found(self, client):
        """Returns 404 for non-existent signature request."""
        mock_repo = AsyncMock()
        mock_repo.get_by_id.return_value = None

        with patch(
            "api.routers.esignatures.SignatureRequestRepository",
            return_value=mock_repo,
        ):
            resp = await client.get("/api/v1/signatures/nonexistent-id")
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_cancel_signature_request_not_found(self, client):
        """Returns 404 when cancelling non-existent request."""
        mock_repo = AsyncMock()
        mock_repo.get_by_id.return_value = None

        with (
            patch(
                "api.routers.esignatures.SignatureRequestRepository",
                return_value=mock_repo,
            ),
            patch("api.routers.esignatures.get_esignature_service", return_value=None),
        ):
            resp = await client.post("/api/v1/signatures/nonexistent-id/cancel")
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_send_reminder_not_found(self, client):
        """Returns 404 when sending reminder for non-existent request."""
        mock_repo = AsyncMock()
        mock_repo.get_by_id.return_value = None

        with (
            patch(
                "api.routers.esignatures.SignatureRequestRepository",
                return_value=mock_repo,
            ),
            patch("api.routers.esignatures.get_esignature_service", return_value=None),
        ):
            resp = await client.post("/api/v1/signatures/nonexistent-id/reminder")
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_download_not_completed(self, client):
        """Returns 400 when downloading non-completed request."""
        sig_request = _make_signature_request_mock(status="sent")
        mock_repo = MagicMock()
        mock_repo.get_by_id = AsyncMock(return_value=sig_request)

        with (
            patch(
                "api.routers.esignatures.SignatureRequestRepository",
                return_value=mock_repo,
            ),
            patch("api.routers.esignatures.get_esignature_service", return_value=None),
            patch("api.routers.esignatures.get_document_storage", return_value=MagicMock()),
        ):
            resp = await client.get("/api/v1/signatures/sig-001/download")
        assert resp.status_code == 400
