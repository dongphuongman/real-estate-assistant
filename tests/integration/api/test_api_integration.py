from unittest.mock import patch

from fastapi.testclient import TestClient
from langchain_core.documents import Document

from api.dependencies import get_vector_store
from api.main import app
from config.settings import get_settings
from notifications.notification_preferences import NotificationPreferencesManager

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


def test_rate_limiting_blocks_after_threshold_and_includes_headers():
    settings = get_settings()
    key = settings.api_access_key

    old_enabled = getattr(settings, "api_rate_limit_enabled", False)
    old_rpm = getattr(settings, "api_rate_limit_rpm", 600)
    settings.api_rate_limit_enabled = True
    settings.api_rate_limit_rpm = 2

    try:
        app.state.rate_limiter.reset()

        r1 = client.get("/api/v1/verify-auth", headers={"X-API-Key": key})
        r2 = client.get("/api/v1/verify-auth", headers={"X-API-Key": key})
        r3 = client.get("/api/v1/verify-auth", headers={"X-API-Key": key})

        assert r1.status_code == 200
        assert r2.status_code == 200
        assert r3.status_code == 429
        assert r3.headers.get("retry-after")
        assert r3.headers.get("x-request-id")
        assert r3.headers.get("x-ratelimit-limit") == "2"
        assert r3.headers.get("x-ratelimit-remaining") == "0"
        assert r3.headers.get("x-ratelimit-reset")
    finally:
        settings.api_rate_limit_enabled = old_enabled
        settings.api_rate_limit_rpm = old_rpm
        app.state.rate_limiter.reset()


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


def test_notification_settings_are_scoped_by_user_email(tmp_path):
    settings = get_settings()
    key = settings.api_access_key

    prefs_manager = NotificationPreferencesManager(storage_path=str(tmp_path))

    with patch("api.routers.settings.PREFS_MANAGER", prefs_manager):
        user1_headers = {"X-API-Key": key, "X-User-Email": "user1@example.com"}
        user2_headers = {"X-API-Key": key, "X-User-Email": "user2@example.com"}

        r1 = client.put(
            "/api/v1/settings/notifications",
            json={
                "email_digest": True,
                "frequency": "daily",
                "expert_mode": True,
                "marketing_emails": False,
            },
            headers=user1_headers,
        )
        assert r1.status_code == 200

        r2 = client.put(
            "/api/v1/settings/notifications",
            json={
                "email_digest": False,
                "frequency": "weekly",
                "expert_mode": False,
                "marketing_emails": True,
            },
            headers=user2_headers,
        )
        assert r2.status_code == 200

        g1 = client.get("/api/v1/settings/notifications", headers=user1_headers)
        g2 = client.get("/api/v1/settings/notifications", headers=user2_headers)

        assert g1.status_code == 200
        assert g2.status_code == 200

        d1 = g1.json()
        d2 = g2.json()

        assert d1["frequency"] == "daily"
        assert d1["email_digest"] is True
        assert d1["expert_mode"] is True
        assert d1["marketing_emails"] is False

        assert d2["frequency"] == "weekly"
        assert d2["email_digest"] is False
        assert d2["expert_mode"] is False
        assert d2["marketing_emails"] is True


def test_notification_settings_requires_user_email(tmp_path):
    settings = get_settings()
    key = settings.api_access_key

    prefs_manager = NotificationPreferencesManager(storage_path=str(tmp_path))

    with patch("api.routers.settings.PREFS_MANAGER", prefs_manager):
        headers = {"X-API-Key": key}

        r_get = client.get("/api/v1/settings/notifications", headers=headers)
        assert r_get.status_code == 400
        assert r_get.json()["detail"] == "Missing user email"

        r_put = client.put(
            "/api/v1/settings/notifications",
            json={
                "email_digest": True,
                "frequency": "weekly",
                "expert_mode": False,
                "marketing_emails": False,
            },
            headers=headers,
        )
        assert r_put.status_code == 400
        assert r_put.json()["detail"] == "Missing user email"


def test_model_catalog_lists_providers_and_models():
    settings = get_settings()
    key = settings.api_access_key

    response = client.get("/api/v1/settings/models", headers={"X-API-Key": key})
    assert response.status_code == 200

    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 1

    provider_names = {p["name"] for p in data}
    assert "openai" in provider_names
    assert "ollama" in provider_names

    openai = next(p for p in data if p["name"] == "openai")
    assert openai["requires_api_key"] is True
    assert openai["is_local"] is False
    assert isinstance(openai["models"], list)
    assert len(openai["models"]) >= 1

    m = openai["models"][0]
    assert m["id"]
    assert m["display_name"]
    assert m["provider_name"]
    assert isinstance(m["context_window"], int)
    assert isinstance(m["capabilities"], list)

    ollama = next(p for p in data if p["name"] == "ollama")
    assert ollama["is_local"] is True
    assert isinstance(ollama["runtime_available"], bool)
    assert isinstance(ollama["available_models"], list)
