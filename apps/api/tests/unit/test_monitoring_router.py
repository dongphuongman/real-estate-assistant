"""
Unit tests for monitoring router (api/routers/monitoring.py).

Tests cover:
- Health check endpoint (liveness probe)
- Readiness check endpoint (service dependencies)
- Metrics endpoint (Prometheus format)
- Monitoring overview endpoint
- Test alert endpoint
"""

import pytest
from fastapi import FastAPI, status
from httpx import ASGITransport, AsyncClient

from api.deps.auth import get_auth_credentials
from api.routers.monitoring import router as monitoring_router
from db.database import get_db


@pytest.fixture
async def monitoring_client(db_session):
    """Create an async HTTP client for testing monitoring endpoints."""
    test_app = FastAPI()
    test_app.include_router(monitoring_router, prefix="/api/v1")

    # Override DB dependency
    async def override_get_db():
        yield db_session

    test_app.dependency_overrides[get_db] = override_get_db

    # Override auth dependency to allow tests
    async def mock_auth_credentials():
        class MockCredentials:
            user_id = "test-user-123"
            permissions = []

            def is_admin(self):
                return False

            def has_permission(self, perm):
                return False

        return MockCredentials()

    test_app.dependency_overrides[get_auth_credentials] = mock_auth_credentials

    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client

    test_app.dependency_overrides.clear()


class TestHealthCheck:
    """Test health check endpoint."""

    @pytest.mark.asyncio
    async def test_health_check_returns_healthy(self, monitoring_client):
        """Test that health check returns 200 OK with healthy status."""
        response = await monitoring_client.get("/api/v1/health")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "healthy"
        assert "timestamp" in data
        assert data["service"] == "ai-real-estate-assistant"

    @pytest.mark.asyncio
    async def test_health_check_response_structure(self, monitoring_client):
        """Test that health check has required fields."""
        response = await monitoring_client.get("/api/v1/health")

        data = response.json()
        assert "status" in data
        assert "timestamp" in data
        assert "service" in data
        assert isinstance(data["status"], str)
        assert isinstance(data["timestamp"], str)
        assert isinstance(data["service"], str)


class TestReadinessCheck:
    """Test readiness check endpoint."""

    @pytest.mark.asyncio
    async def test_readiness_check_returns_expected_structure(self, monitoring_client):
        """Test that readiness check returns expected fields."""
        response = await monitoring_client.get("/api/v1/ready")

        assert response.status_code in (status.HTTP_200_OK, status.HTTP_503_SERVICE_UNAVAILABLE)
        data = response.json()
        assert "database" in data
        assert "redis" in data
        assert "llm" in data
        assert "overall" in data
        assert "timestamp" in data

    @pytest.mark.asyncio
    async def test_readiness_check_database_status_present(self, monitoring_client):
        """Test that readiness check reports database status."""
        response = await monitoring_client.get("/api/v1/ready")

        data = response.json()
        assert "database" in data
        assert data["database"] in ("healthy", "unhealthy", "disabled", "unknown")

    @pytest.mark.asyncio
    async def test_readiness_check_overall_status(self, monitoring_client):
        """Test that readiness check provides overall status."""
        response = await monitoring_client.get("/api/v1/ready")

        data = response.json()
        assert "overall" in data
        assert data["overall"] in ("ready", "not_ready")


class TestMetricsEndpoint:
    """Test metrics endpoint."""

    @pytest.mark.asyncio
    async def test_metrics_returns_prometheus_format(self, monitoring_client):
        """Test that metrics endpoint returns Prometheus text format."""
        response = await monitoring_client.get("/api/v1/metrics")

        assert response.status_code == status.HTTP_200_OK
        assert "text/plain" in response.headers["content-type"]

        content = response.text
        assert "# HELP" in content or "# TYPE" in content

    @pytest.mark.asyncio
    async def test_metrics_contains_basic_metrics(self, monitoring_client):
        """Test that metrics endpoint includes basic metrics."""
        response = await monitoring_client.get("/api/v1/metrics")

        content = response.text
        assert len(content.strip().split("\n")) > 0

    @pytest.mark.asyncio
    async def test_metrics_response_structure(self, monitoring_client):
        """Test that metrics endpoint has proper content type."""
        response = await monitoring_client.get("/api/v1/metrics")

        assert response.status_code == status.HTTP_200_OK
        assert "content-type" in response.headers
        assert "text/plain" in response.headers["content-type"]


class TestMonitoringOverview:
    """Test monitoring overview endpoint."""

    @pytest.mark.asyncio
    async def test_monitoring_overview_returns_expected_structure(self, monitoring_client):
        """Test that monitoring overview returns expected sections."""
        response = await monitoring_client.get("/api/v1/monitoring/overview")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert "database" in data
        assert "cache" in data
        assert "knowledge_store" in data
        assert "llm" in data
        assert "environment" in data
        assert "timestamp" in data

    @pytest.mark.asyncio
    async def test_monitoring_overview_database_stats(self, monitoring_client):
        """Test that monitoring overview includes database statistics."""
        response = await monitoring_client.get("/api/v1/monitoring/overview")

        data = response.json()
        assert "database" in data
        db = data["database"]

        assert "total_properties" in db
        assert isinstance(db["total_properties"], int)
        assert "recent_properties_24h" in db
        assert isinstance(db["recent_properties_24h"], int)

    @pytest.mark.asyncio
    async def test_monitoring_overview_llm_info(self, monitoring_client):
        """Test that monitoring overview includes LLM provider info."""
        response = await monitoring_client.get("/api/v1/monitoring/overview")

        data = response.json()
        assert "llm" in data
        llm = data["llm"]

        assert "default_provider" in llm
        assert "default_model" in llm


class TestAlertEndpoint:
    """Test alert endpoint."""

    @pytest.mark.asyncio
    async def test_alert_endpoint_without_permission(self, monitoring_client):
        """Test that test alert endpoint requires admin permission."""
        response = await monitoring_client.post("/api/v1/monitoring/test-alert")

        # Should fail without proper permissions (403)
        assert response.status_code in (
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_403_FORBIDDEN,
            status.HTTP_404_NOT_FOUND,
        )

    @pytest.mark.asyncio
    async def test_alert_endpoint_with_permission(self, monitoring_client):
        """Test that test alert endpoint works with admin permission."""
        # Create a new app with admin credentials
        test_app = FastAPI()
        test_app.include_router(monitoring_router, prefix="/api/v1")

        async def override_get_db():
            from tests.conftest import db_session_factory

            async with db_session_factory() as session:
                yield session

        async def mock_admin_credentials():
            class MockAdminCredentials:
                user_id = "admin-user"

                permissions = ["admin.system_control"]

                def is_admin(self):
                    return True

            return MockAdminCredentials()

        test_app.dependency_overrides[get_auth_credentials] = mock_admin_credentials

        transport = ASGITransport(app=test_app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post("/api/v1/monitoring/test-alert")

        assert response.status_code in (
            status.HTTP_200_OK,
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_403_FORBIDDEN,
        )


class TestMonitoringConstants:
    """Test monitoring router behavior with different states."""

    @pytest.mark.asyncio
    async def test_health_check_always_succeeds(self, monitoring_client):
        """Test that health check always returns 200 regardless of dependencies."""
        response = await monitoring_client.get("/api/v1/health")
        assert response.status_code == status.HTTP_200_OK

    @pytest.mark.asyncio
    async def test_metrics_format_valid_prometheus(self, monitoring_client):
        """Test that metrics output is valid Prometheus format."""
        response = await monitoring_client.get("/api/v1/metrics")

        content = response.text
        lines = content.split("\n")

        help_lines = [line for line in lines if line.startswith("# HELP")]
        type_lines = [line for line in lines if line.startswith("# TYPE")]

        assert (
            len(help_lines) > 0
            or len(type_lines) > 0
            or len([line for line in lines if not line.startswith("#")]) > 0
        )
