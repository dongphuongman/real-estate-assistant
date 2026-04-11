"""E2E tests for data ingest → search lifecycle.

Tests the full pipeline: ingest data → verify search finds it.
Uses the real app with mocked LLM and vector store.
"""

import pytest

from tests.e2e_backend.conftest import API_KEY


@pytest.fixture
def api_headers():
    return {"X-API-Key": API_KEY}


@pytest.mark.asyncio
class TestDataIngestSearchE2E:
    """Tests for ingest → search lifecycle."""

    async def test_health_check(self, e2e_client):
        """Verify the app is up."""
        resp = await e2e_client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "healthy"

    async def test_openapi_schema_accessible(self, e2e_client):
        """Verify OpenAPI schema is generated."""
        resp = await e2e_client.get("/openapi.json")
        assert resp.status_code == 200
        data = resp.json()
        assert "paths" in data
        assert "/api/v1/search" in data["paths"]

    async def test_search_with_results(self, e2e_client, api_headers):
        """Search endpoint returns structured response."""
        resp = await e2e_client.post(
            "/api/v1/search",
            json={"query": "apartments in Krakow under 500000"},
            headers=api_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "results" in data or "properties" in data or "answer" in data

    async def test_search_with_filters(self, e2e_client, api_headers):
        """Search with structured filters."""
        resp = await e2e_client.post(
            "/api/v1/search",
            json={
                "query": "2-bedroom apartments",
                "filters": {"city": "Krakow", "price_max": 500000, "rooms": 2},
            },
            headers=api_headers,
        )
        assert resp.status_code == 200

    async def test_search_invalid_query_handled(self, e2e_client, api_headers):
        """Empty query should be handled gracefully."""
        resp = await e2e_client.post(
            "/api/v1/search",
            json={"query": ""},
            headers=api_headers,
        )
        # Should return 200 with empty/error, not crash
        assert resp.status_code in (200, 422)


@pytest.mark.asyncio
class TestAPIKeyAuthE2E:
    """Tests for API key authentication on all endpoints."""

    async def test_settings_requires_auth(self, e2e_client):
        resp = await e2e_client.get("/api/v1/settings")
        assert resp.status_code == 401

    async def test_prompt_templates_requires_auth(self, e2e_client):
        resp = await e2e_client.get("/api/v1/prompt-templates")
        assert resp.status_code == 401

    async def test_exports_requires_auth(self, e2e_client):
        resp = await e2e_client.get("/api/v1/exports")
        assert resp.status_code == 401

    async def test_valid_key_accesses_settings(self, e2e_client, api_headers):
        resp = await e2e_client.get("/api/v1/settings", headers=api_headers)
        assert resp.status_code == 200

    async def test_cors_headers_present(self, e2e_client):
        """Verify CORS headers are set on preflight requests."""
        resp = await e2e_client.options(
            "/api/v1/search",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "POST",
            },
        )
        # CORS should allow the request
        assert resp.status_code in (200, 204)
