from fastapi.testclient import TestClient
from api.main import app
from config.settings import get_settings
from api.dependencies import get_vector_store
from langchain_core.documents import Document

client = TestClient(app)


def test_health_check():
    """Test health check endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "version" in data


def test_protected_route_no_auth():
    """Test protected route without auth headers."""
    response = client.get("/api/v1/verify-auth")
    # FastAPI Security with auto_error=False passes None, but our logic raises 401
    assert response.status_code == 401
    assert response.json()["detail"] == "Missing API Key"


def test_protected_route_invalid_auth():
    """Test protected route with invalid auth."""
    response = client.get("/api/v1/verify-auth", headers={"X-API-Key": "wrong-key"})
    assert response.status_code == 403
    assert response.json()["detail"] == "Could not validate credentials"


def test_protected_route_valid_auth():
    """Test protected route with valid auth."""
    # We need to ensure we use the key that the app is currently using
    settings = get_settings()
    key = settings.api_access_key

    response = client.get("/api/v1/verify-auth", headers={"X-API-Key": key})
    assert response.status_code == 200
    assert response.json()["valid"] is True


def test_request_id_is_added_to_responses():
    response = client.get("/health")
    assert response.headers.get("x-request-id")


def test_request_id_is_echoed_when_provided():
    request_id = "test-req-123"
    response = client.get("/health", headers={"X-Request-ID": request_id})
    assert response.headers.get("x-request-id") == request_id


def test_request_id_is_present_on_error_responses():
    request_id = "test-req-err"
    response = client.get("/api/v1/verify-auth", headers={"X-Request-ID": request_id})
    assert response.status_code == 401
    assert response.headers.get("x-request-id") == request_id


def test_tools_auth_enforced():
    response = client.post("/api/v1/tools/price-analysis", json={"query": "x"})
    assert response.status_code == 401

    response = client.post(
        "/api/v1/tools/price-analysis",
        json={"query": "x"},
        headers={"X-API-Key": "wrong-key"},
    )
    assert response.status_code == 403


def test_tools_compare_properties_happy_path_with_stub_store():
    settings = get_settings()
    key = settings.api_access_key

    class _Store:
        def get_properties_by_ids(self, property_ids):
            return [
                Document(page_content="a", metadata={"id": "p1", "price": 100000}),
                Document(page_content="b", metadata={"id": "p2", "price": 150000}),
            ]

    app.dependency_overrides[get_vector_store] = lambda: _Store()

    response = client.post(
        "/api/v1/tools/compare-properties",
        json={"property_ids": ["p1", "p2"]},
        headers={"X-API-Key": key},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["summary"]["count"] == 2
    assert data["summary"]["price_difference"] == 50000

    app.dependency_overrides = {}
