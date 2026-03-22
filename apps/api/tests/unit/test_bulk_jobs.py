"""Unit tests for bulk jobs router.

Tests cover import/export job creation, status tracking, and cancellation.
"""

import os
from collections.abc import AsyncGenerator
from datetime import UTC, datetime
from unittest.mock import patch

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

os.environ.setdefault("ENVIRONMENT", "test")
os.environ.setdefault("API_ACCESS_KEY", "test-api-key")

from api.auth import get_api_key
from api.routers import bulk_jobs
from db.database import get_db
from db.models import BulkJob


@pytest.fixture
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """Create async client with bulk jobs router."""
    app = FastAPI()

    async def override_get_api_key():
        return "test-api-key"

    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_api_key] = override_get_api_key
    app.dependency_overrides[get_db] = override_get_db

    app.include_router(bulk_jobs.router, prefix="/api/v1")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest.fixture
def auth_headers() -> dict[str, str]:
    """API key auth headers."""
    return {"X-API-Key": "test-api-key"}


@pytest.fixture
async def sample_import_job(db_session: AsyncSession) -> BulkJob:
    """Create a sample import job for testing."""
    job = BulkJob(
        id="test-import-001",
        job_type="import",
        source_type="url",
        config={
            "file_urls": ["https://example.com/data.csv"],
            "source_name": "Test Import",
        },
        status="completed",
        records_total=100,
        records_processed=100,
        records_failed=0,
        progress_percent=100.0,
        result_data={"records_processed": 100},
    )
    db_session.add(job)
    await db_session.flush()
    await db_session.refresh(job)
    return job


@pytest.fixture
async def sample_export_job(db_session: AsyncSession) -> BulkJob:
    """Create a sample export job for testing."""
    job = BulkJob(
        id="test-export-001",
        job_type="export",
        source_type="search",
        config={
            "format": "csv",
            "query": "apartments in Warsaw",
            "limit": 50,
        },
        status="completed",
        records_total=50,
        records_processed=50,
        records_failed=0,
        progress_percent=100.0,
        result_data={"format": "csv", "records_exported": 50},
    )
    db_session.add(job)
    await db_session.flush()
    await db_session.refresh(job)
    return job


@pytest.fixture
async def sample_pending_job(db_session: AsyncSession) -> BulkJob:
    """Create a pending job for cancellation tests."""
    job = BulkJob(
        id="test-pending-001",
        job_type="import",
        source_type="url",
        config={"file_urls": ["https://example.com/data.csv"]},
        status="pending",
        records_total=0,
        records_processed=0,
        records_failed=0,
        progress_percent=0.0,
    )
    db_session.add(job)
    await db_session.flush()
    await db_session.refresh(job)
    return job


class TestListBulkJobs:
    """Tests for listing bulk jobs."""

    @pytest.mark.asyncio
    async def test_list_empty(self, client: AsyncClient, auth_headers: dict):
        """Test listing when no jobs exist."""
        response = await client.get("/api/v1/bulk-jobs", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0
        assert data["jobs"] == []
        assert data["page"] == 1
        assert data["page_size"] == 20

    @pytest.mark.asyncio
    async def test_list_with_jobs(
        self,
        client: AsyncClient,
        auth_headers: dict,
        sample_import_job: BulkJob,
        sample_export_job: BulkJob,
    ):
        """Test listing with existing jobs."""
        response = await client.get("/api/v1/bulk-jobs", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2
        assert len(data["jobs"]) == 2

    @pytest.mark.asyncio
    async def test_list_pagination(
        self, client: AsyncClient, auth_headers: dict, db_session: AsyncSession
    ):
        """Test pagination parameters."""
        for i in range(25):
            job = BulkJob(
                id=f"job-{i:03d}",
                job_type="import",
                source_type="url",
                config={"file_urls": [f"https://example.com/data{i}.csv"]},
                status="completed",
            )
            db_session.add(job)
        await db_session.flush()

        response = await client.get("/api/v1/bulk-jobs?page=1&page_size=10", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 25
        assert len(data["jobs"]) == 10
        assert data["page"] == 1

        response = await client.get("/api/v1/bulk-jobs?page=2&page_size=10", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data["jobs"]) == 10
        assert data["page"] == 2

    @pytest.mark.asyncio
    async def test_list_filter_by_job_type(
        self, client: AsyncClient, auth_headers: dict, db_session: AsyncSession
    ):
        """Test filtering by job type."""
        for jtype in ["import", "export"]:
            job = BulkJob(
                id=f"job-{jtype}",
                job_type=jtype,
                source_type="url",
                config={},
                status="completed",
            )
            db_session.add(job)
        await db_session.flush()

        response = await client.get("/api/v1/bulk-jobs?job_type=import", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["jobs"][0]["job_type"] == "import"

    @pytest.mark.asyncio
    async def test_list_filter_by_status(
        self, client: AsyncClient, auth_headers: dict, db_session: AsyncSession
    ):
        """Test filtering by status."""
        for status_val in ["completed", "failed", "pending"]:
            job = BulkJob(
                id=f"job-{status_val}",
                job_type="import",
                source_type="url",
                config={},
                status=status_val,
            )
            db_session.add(job)
        await db_session.flush()

        response = await client.get("/api/v1/bulk-jobs?status=completed", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["jobs"][0]["status"] == "completed"

    @pytest.mark.asyncio
    async def test_list_filter_by_source_type(
        self, client: AsyncClient, auth_headers: dict, db_session: AsyncSession
    ):
        """Test filtering by source type."""
        for stype in ["url", "portal_api", "search"]:
            job = BulkJob(
                id=f"job-{stype}",
                job_type="import" if stype != "search" else "export",
                source_type=stype,
                config={},
                status="completed",
            )
            db_session.add(job)
        await db_session.flush()

        response = await client.get("/api/v1/bulk-jobs?source_type=url", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["jobs"][0]["source_type"] == "url"


class TestGetBulkJob:
    """Tests for getting a single bulk job."""

    @pytest.mark.asyncio
    async def test_get_existing_job(
        self, client: AsyncClient, auth_headers: dict, sample_import_job: BulkJob
    ):
        """Test getting an existing job."""
        response = await client.get(
            f"/api/v1/bulk-jobs/{sample_import_job.id}", headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == sample_import_job.id
        assert data["job_type"] == "import"
        assert data["status"] == "completed"
        assert data["records_total"] == 100
        assert data["progress_percent"] == 100.0

    @pytest.mark.asyncio
    async def test_get_nonexistent_job(self, client: AsyncClient, auth_headers: dict):
        """Test getting a non-existent job."""
        response = await client.get("/api/v1/bulk-jobs/nonexistent-id", headers=auth_headers)
        assert response.status_code == 404
        assert "not found" in response.json()["detail"]


class TestCreateImportJob:
    """Tests for creating import jobs."""

    @pytest.mark.asyncio
    async def test_create_url_import(self, client: AsyncClient, auth_headers: dict):
        """Test creating a URL import job."""
        with patch("api.routers.bulk_jobs.BackgroundTasks.add_task") as mock_add_task:
            response = await client.post(
                "/api/v1/bulk-jobs/import",
                headers=auth_headers,
                json={
                    "source_type": "url",
                    "config": {
                        "file_urls": ["https://example.com/data.csv"],
                    },
                    "source_name": "Test Import",
                },
            )
        assert response.status_code == 201
        data = response.json()
        assert data["job_type"] == "import"
        assert data["status"] == "pending"
        assert "id" in data
        assert data["message"] == "Import job started"
        mock_add_task.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_url_import_multiple_files(self, client: AsyncClient, auth_headers: dict):
        """Test creating import with multiple URLs."""
        with patch("api.routers.bulk_jobs.BackgroundTasks.add_task"):
            response = await client.post(
                "/api/v1/bulk-jobs/import",
                headers=auth_headers,
                json={
                    "source_type": "url",
                    "config": {
                        "file_urls": [
                            "https://example.com/data1.csv",
                            "https://example.com/data2.csv",
                        ],
                    },
                },
            )
        assert response.status_code == 201
        data = response.json()
        assert data["job_type"] == "import"

    @pytest.mark.asyncio
    async def test_create_url_import_missing_urls(self, client: AsyncClient, auth_headers: dict):
        """Test validation fails when URLs missing."""
        response = await client.post(
            "/api/v1/bulk-jobs/import",
            headers=auth_headers,
            json={
                "source_type": "url",
                "config": {},
            },
        )
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_create_url_import_invalid_url(self, client: AsyncClient, auth_headers: dict):
        """Test validation fails for invalid URL."""
        response = await client.post(
            "/api/v1/bulk-jobs/import",
            headers=auth_headers,
            json={
                "source_type": "url",
                "config": {
                    "file_urls": ["not-a-valid-url"],
                },
            },
        )
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_create_file_upload_import(self, client: AsyncClient, auth_headers: dict):
        """Test creating a file upload import job."""
        with patch("api.routers.bulk_jobs.BackgroundTasks.add_task"):
            response = await client.post(
                "/api/v1/bulk-jobs/import",
                headers=auth_headers,
                json={
                    "source_type": "file_upload",
                    "config": {
                        "temp_file_path": "/tmp/upload123.csv",
                        "filename": "upload.csv",
                    },
                },
            )
        assert response.status_code == 201
        data = response.json()
        assert data["job_type"] == "import"

    @pytest.mark.asyncio
    async def test_create_portal_import(self, client: AsyncClient, auth_headers: dict):
        """Test creating a portal API import job."""
        with patch("api.routers.bulk_jobs.BackgroundTasks.add_task"):
            response = await client.post(
                "/api/v1/bulk-jobs/import",
                headers=auth_headers,
                json={
                    "source_type": "portal_api",
                    "config": {
                        "portal": "overpass",
                        "city": "Warsaw",
                        "filters": {"listing_type": "rent"},
                        "limit": 50,
                    },
                },
            )
        assert response.status_code == 201
        data = response.json()
        assert data["job_type"] == "import"


class TestCreateExportJob:
    """Tests for creating export jobs."""

    @pytest.mark.asyncio
    async def test_create_csv_export(self, client: AsyncClient, auth_headers: dict):
        """Test creating a CSV export job."""
        with patch("api.routers.bulk_jobs.BackgroundTasks.add_task") as mock_add_task:
            response = await client.post(
                "/api/v1/bulk-jobs/export",
                headers=auth_headers,
                json={
                    "format": "csv",
                    "source_type": "search",
                    "config": {
                        "query": "apartments in Warsaw",
                        "limit": 50,
                    },
                    "include_header": True,
                },
            )
        assert response.status_code == 201
        data = response.json()
        assert data["job_type"] == "export"
        assert data["status"] == "pending"
        mock_add_task.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_parquet_export(self, client: AsyncClient, auth_headers: dict):
        """Test creating a Parquet export job."""
        with patch("api.routers.bulk_jobs.BackgroundTasks.add_task"):
            response = await client.post(
                "/api/v1/bulk-jobs/export",
                headers=auth_headers,
                json={
                    "format": "parquet",
                    "source_type": "search",
                    "config": {
                        "query": "apartments",
                        "limit": 100,
                    },
                },
            )
        assert response.status_code == 201
        data = response.json()
        assert data["job_type"] == "export"

    @pytest.mark.asyncio
    async def test_create_export_with_columns(self, client: AsyncClient, auth_headers: dict):
        """Test creating export with specific columns."""
        with patch("api.routers.bulk_jobs.BackgroundTasks.add_task"):
            response = await client.post(
                "/api/v1/bulk-jobs/export",
                headers=auth_headers,
                json={
                    "format": "json",
                    "source_type": "search",
                    "config": {"query": "apartments"},
                    "columns": ["id", "price", "city", "rooms"],
                },
            )
        assert response.status_code == 201

    @pytest.mark.asyncio
    async def test_create_export_invalid_format(self, client: AsyncClient, auth_headers: dict):
        """Test validation fails for invalid format."""
        response = await client.post(
            "/api/v1/bulk-jobs/export",
            headers=auth_headers,
            json={
                "format": "invalid_format",
                "source_type": "search",
                "config": {"query": "test"},
            },
        )
        assert response.status_code == 400
        assert "Invalid format" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_create_export_with_property_ids(self, client: AsyncClient, auth_headers: dict):
        """Test creating export with specific property IDs."""
        with patch("api.routers.bulk_jobs.BackgroundTasks.add_task"):
            response = await client.post(
                "/api/v1/bulk-jobs/export",
                headers=auth_headers,
                json={
                    "format": "xlsx",
                    "source_type": "search",
                    "config": {
                        "property_ids": ["prop-1", "prop-2", "prop-3"],
                    },
                },
            )
        assert response.status_code == 201


class TestCancelBulkJob:
    """Tests for cancelling bulk jobs."""

    @pytest.mark.asyncio
    async def test_cancel_pending_job(
        self, client: AsyncClient, auth_headers: dict, sample_pending_job: BulkJob
    ):
        """Test cancelling a pending job."""
        response = await client.post(
            f"/api/v1/bulk-jobs/{sample_pending_job.id}/cancel", headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "cancelled"
        assert data["error_message"] == "Job cancelled by user"

    @pytest.mark.asyncio
    async def test_cancel_running_job(
        self, client: AsyncClient, auth_headers: dict, db_session: AsyncSession
    ):
        """Test cancelling a running job."""
        job = BulkJob(
            id="test-running-001",
            job_type="import",
            source_type="url",
            config={},
            status="running",
            started_at=datetime.now(UTC),
        )
        db_session.add(job)
        await db_session.flush()

        response = await client.post(f"/api/v1/bulk-jobs/{job.id}/cancel", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "cancelled"

    @pytest.mark.asyncio
    async def test_cancel_completed_job(
        self, client: AsyncClient, auth_headers: dict, sample_import_job: BulkJob
    ):
        """Test cannot cancel a completed job."""
        response = await client.post(
            f"/api/v1/bulk-jobs/{sample_import_job.id}/cancel", headers=auth_headers
        )
        assert response.status_code == 400
        assert "Cannot cancel" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_cancel_nonexistent_job(self, client: AsyncClient, auth_headers: dict):
        """Test cancelling a non-existent job."""
        response = await client.post(
            "/api/v1/bulk-jobs/nonexistent-id/cancel", headers=auth_headers
        )
        assert response.status_code == 404


class TestDeleteBulkJob:
    """Tests for deleting bulk jobs."""

    @pytest.mark.asyncio
    async def test_delete_completed_job(
        self, client: AsyncClient, auth_headers: dict, sample_import_job: BulkJob
    ):
        """Test deleting a completed job."""
        response = await client.delete(
            f"/api/v1/bulk-jobs/{sample_import_job.id}", headers=auth_headers
        )
        assert response.status_code == 204

    @pytest.mark.asyncio
    async def test_delete_failed_job(
        self, client: AsyncClient, auth_headers: dict, db_session: AsyncSession
    ):
        """Test deleting a failed job."""
        job = BulkJob(
            id="test-failed-001",
            job_type="import",
            source_type="url",
            config={},
            status="failed",
            error_message="Something went wrong",
        )
        db_session.add(job)
        await db_session.flush()

        response = await client.delete(f"/api/v1/bulk-jobs/{job.id}", headers=auth_headers)
        assert response.status_code == 204

    @pytest.mark.asyncio
    async def test_delete_cancelled_job(
        self, client: AsyncClient, auth_headers: dict, db_session: AsyncSession
    ):
        """Test deleting a cancelled job."""
        job = BulkJob(
            id="test-cancelled-001",
            job_type="import",
            source_type="url",
            config={},
            status="cancelled",
        )
        db_session.add(job)
        await db_session.flush()

        response = await client.delete(f"/api/v1/bulk-jobs/{job.id}", headers=auth_headers)
        assert response.status_code == 204

    @pytest.mark.asyncio
    async def test_delete_pending_job(
        self, client: AsyncClient, auth_headers: dict, sample_pending_job: BulkJob
    ):
        """Test cannot delete a pending job."""
        response = await client.delete(
            f"/api/v1/bulk-jobs/{sample_pending_job.id}", headers=auth_headers
        )
        assert response.status_code == 400
        assert "Cannot delete active job" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_delete_running_job(
        self, client: AsyncClient, auth_headers: dict, db_session: AsyncSession
    ):
        """Test cannot delete a running job."""
        job = BulkJob(
            id="test-running-del-001",
            job_type="import",
            source_type="url",
            config={},
            status="running",
        )
        db_session.add(job)
        await db_session.flush()

        response = await client.delete(f"/api/v1/bulk-jobs/{job.id}", headers=auth_headers)
        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_delete_nonexistent_job(self, client: AsyncClient, auth_headers: dict):
        """Test deleting a non-existent job."""
        response = await client.delete("/api/v1/bulk-jobs/nonexistent-id", headers=auth_headers)
        assert response.status_code == 404


class TestJobProgress:
    """Tests for job progress tracking."""

    @pytest.mark.asyncio
    async def test_job_response_includes_progress(
        self, client: AsyncClient, auth_headers: dict, sample_import_job: BulkJob
    ):
        """Test that job response includes progress fields."""
        response = await client.get(
            f"/api/v1/bulk-jobs/{sample_import_job.id}", headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert "records_total" in data
        assert "records_processed" in data
        assert "records_failed" in data
        assert "progress_percent" in data

    @pytest.mark.asyncio
    async def test_job_response_includes_timestamps(
        self, client: AsyncClient, auth_headers: dict, db_session: AsyncSession
    ):
        """Test that job response includes timestamps."""
        job = BulkJob(
            id="test-timestamps-001",
            job_type="import",
            source_type="url",
            config={},
            status="completed",
            started_at=datetime.now(UTC),
            completed_at=datetime.now(UTC),
        )
        db_session.add(job)
        await db_session.flush()

        response = await client.get(f"/api/v1/bulk-jobs/{job.id}", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "created_at" in data
        assert "started_at" in data
        assert "completed_at" in data

    @pytest.mark.asyncio
    async def test_job_response_includes_result_data(
        self, client: AsyncClient, auth_headers: dict, sample_export_job: BulkJob
    ):
        """Test that completed job includes result data."""
        response = await client.get(
            f"/api/v1/bulk-jobs/{sample_export_job.id}", headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["result_data"] is not None
        assert "format" in data["result_data"]
        assert "records_exported" in data["result_data"]


class TestValidation:
    """Tests for input validation."""

    @pytest.mark.asyncio
    async def test_import_invalid_source_type(self, client: AsyncClient, auth_headers: dict):
        """Test validation fails for invalid source type."""
        response = await client.post(
            "/api/v1/bulk-jobs/import",
            headers=auth_headers,
            json={
                "source_type": "invalid_type",
                "config": {},
            },
        )
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_export_missing_config(self, client: AsyncClient, auth_headers: dict):
        """Test validation fails when config is missing required fields."""
        response = await client.post(
            "/api/v1/bulk-jobs/export",
            headers=auth_headers,
            json={
                "format": "csv",
                "source_type": "search",
                "config": {},  # Missing query/filters/property_ids
            },
        )
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_pagination_limits(self, client: AsyncClient, auth_headers: dict):
        """Test pagination parameter limits."""
        # page_size too large
        response = await client.get("/api/v1/bulk-jobs?page_size=200", headers=auth_headers)
        assert response.status_code == 422

        # page < 1
        response = await client.get("/api/v1/bulk-jobs?page=0", headers=auth_headers)
        assert response.status_code == 422
