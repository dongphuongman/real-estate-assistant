import pytest
from fastapi.testclient import TestClient


@pytest.mark.timeout(120)
def test_health_endpoint_returns_healthy():
    from api.main import app

    with TestClient(app) as client:
        resp = client.get("/health?include_dependencies=false")
        assert resp.status_code == 200
        data = resp.json()
        assert data.get("status") == "healthy"
        assert "timestamp" in data
