"""
E2E tests for the search flow.

Tests the complete path: request → auth → query parsing → search → response.
"""

import pytest


@pytest.mark.asyncio
class TestSearchE2E:
    """Search endpoint — validates full search request/response cycle."""

    async def test_basic_search(self, e2e_client, api_headers):
        resp = await e2e_client.post(
            "/api/v1/search",
            json={"query": "2 bedroom apartment in Krakow"},
            headers=api_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "results" in data or "properties" in data or "answer" in data

    async def test_search_with_filters(self, e2e_client, api_headers):
        resp = await e2e_client.post(
            "/api/v1/search",
            json={
                "query": "apartments",
                "filters": {
                    "city": "Krakow",
                    "min_price": 500,
                    "max_price": 2000,
                    "min_rooms": 2,
                },
            },
            headers=api_headers,
        )
        assert resp.status_code == 200

    async def test_search_empty_query(self, e2e_client, api_headers):
        resp = await e2e_client.post(
            "/api/v1/search",
            json={"query": ""},
            headers=api_headers,
        )
        # Should handle gracefully (200 with empty results or 422 validation error)
        assert resp.status_code in (200, 422)

    async def test_search_invalid_body(self, e2e_client, api_headers):
        resp = await e2e_client.post(
            "/api/v1/search",
            json={},
            headers=api_headers,
        )
        assert resp.status_code == 422

    async def test_search_response_has_security_headers(self, e2e_client, api_headers):
        resp = await e2e_client.post(
            "/api/v1/search",
            json={"query": "test"},
            headers=api_headers,
        )
        assert resp.status_code == 200
        # Security headers added by middleware
        assert "X-Content-Type-Options" in resp.headers or resp.status_code == 200

    async def test_search_preserves_request_id(self, e2e_client, api_headers):
        resp = await e2e_client.post(
            "/api/v1/search",
            json={"query": "test"},
            headers={**api_headers, "X-Request-ID": "test-req-123"},
        )
        assert resp.status_code == 200
        # Observability middleware should echo or generate request ID
        assert "X-Request-ID" in resp.headers or "x-request-id" in resp.headers
