from fastapi.testclient import TestClient
from api.main import app
from config.settings import get_settings

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
