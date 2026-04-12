"""Integration tests for documents router."""

from unittest.mock import AsyncMock, patch

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from api.deps.auth import get_current_active_user
from api.routers import documents
from db.database import get_db
from db.schemas import UserResponse


@pytest.fixture
def test_app(db_session):
    """Create test app with documents router and mocked dependencies."""
    app = FastAPI()
    app.include_router(documents.router, prefix="/api/v1")

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


class TestDocumentsAPI:
    """Integration tests for documents endpoints."""

    @pytest.mark.asyncio
    async def test_list_documents_empty(self, client):
        """Returns empty list when no documents exist."""
        mock_repo = AsyncMock()
        mock_repo.list_for_user.return_value = ([], 0)

        with patch("api.routers.documents.DocumentRepository", return_value=mock_repo):
            resp = await client.get("/api/v1/documents")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_get_document_not_found(self, client):
        """Returns 404 for non-existent document."""
        mock_repo = AsyncMock()
        mock_repo.get_by_id.return_value = None

        with patch("api.routers.documents.DocumentRepository", return_value=mock_repo):
            resp = await client.get("/api/v1/documents/nonexistent-id")
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_document_not_found(self, client):
        """Returns 404 when deleting non-existent document."""
        mock_repo = AsyncMock()
        mock_repo.get_by_id.return_value = None

        with patch("api.routers.documents.DocumentRepository", return_value=mock_repo):
            resp = await client.delete("/api/v1/documents/nonexistent-id")
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_list_documents_with_pagination(self, client):
        """Supports pagination parameters."""
        mock_repo = AsyncMock()
        mock_repo.list_for_user.return_value = ([], 0)

        with patch("api.routers.documents.DocumentRepository", return_value=mock_repo):
            resp = await client.get(
                "/api/v1/documents",
                params={"limit": 10, "offset": 0},
            )
        assert resp.status_code == 200
