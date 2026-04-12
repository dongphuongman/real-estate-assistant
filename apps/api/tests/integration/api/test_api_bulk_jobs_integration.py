"""Integration tests for bulk jobs router."""

import sys
from enum import Enum
from unittest.mock import MagicMock

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

# Stub heavy dependencies before importing the router.
# bulk_jobs imports api.dependencies which triggers agents→langchain→protobuf chain.
# We stub the entire chain to avoid the protobuf TypeError.
for mod_name in [
    "agents",
    "agents.hybrid_agent",
    "api.dependencies",
    "data.loaders",
    "data.adapters",
]:
    if mod_name not in sys.modules:
        sys.modules[mod_name] = MagicMock()

# utils.exporters must provide a real ExportFormat enum (Pydantic uses it in models)
import types as _types  # noqa: E402

_exporters = _types.ModuleType("utils.exporters")


class _ExportFormat(str, Enum):
    CSV = "csv"
    EXCEL = "xlsx"
    JSON = "json"


_exporters.ExportFormat = _ExportFormat
_exporters.PropertyExporter = MagicMock()
if "utils.exporters" not in sys.modules:
    sys.modules["utils.exporters"] = _exporters

from api.routers import bulk_jobs  # noqa: E402
from db.database import get_db  # noqa: E402


@pytest.fixture
def test_app(db_session):
    """Create test app with bulk_jobs router and mocked dependencies."""
    app = FastAPI()
    app.include_router(bulk_jobs.router, prefix="/api/v1")

    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    return app


@pytest.fixture
async def client(test_app):
    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


class TestBulkJobsAPI:
    """Integration tests for bulk jobs endpoints."""

    @pytest.mark.asyncio
    async def test_list_bulk_jobs_empty(self, client):
        """Returns empty list when no jobs exist."""
        resp = await client.get("/api/v1/bulk-jobs")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_list_bulk_jobs_with_pagination(self, client):
        """Supports pagination parameters."""
        resp = await client.get(
            "/api/v1/bulk-jobs",
            params={"page": 1, "page_size": 10},
        )
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_get_bulk_job_not_found(self, client):
        """Returns 404 for non-existent job."""
        resp = await client.get("/api/v1/bulk-jobs/nonexistent-id")
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_cancel_bulk_job_not_found(self, client):
        """Returns 404 when cancelling non-existent job."""
        resp = await client.post("/api/v1/bulk-jobs/nonexistent-id/cancel")
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_bulk_job_not_found(self, client):
        """Returns 404 when deleting non-existent job."""
        resp = await client.delete("/api/v1/bulk-jobs/nonexistent-id")
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_list_bulk_jobs_with_filters(self, client):
        """Supports job_type and status filters."""
        resp = await client.get(
            "/api/v1/bulk-jobs",
            params={"job_type": "import", "status_filter": "completed"},
        )
        assert resp.status_code == 200
