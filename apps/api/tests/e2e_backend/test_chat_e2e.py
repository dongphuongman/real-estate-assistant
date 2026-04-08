"""
E2E tests for the chat flow.

Tests the complete path: request → auth → LLM routing → response.
"""

import pytest


@pytest.mark.asyncio
class TestChatE2E:
    """Chat endpoint — validates full chat request/response cycle."""

    async def test_basic_chat(self, e2e_client, api_headers):
        resp = await e2e_client.post(
            "/api/v1/chat",
            json={"message": "What properties are available in Warsaw?"},
            headers=api_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "response" in data or "answer" in data or "message" in data

    async def test_chat_streaming_request(self, e2e_client, api_headers):
        resp = await e2e_client.post(
            "/api/v1/chat",
            json={"message": "test", "stream": True},
            headers=api_headers,
        )
        # Streaming may return 200 with SSE or fall back to non-streaming
        assert resp.status_code == 200

    async def test_chat_empty_message(self, e2e_client, api_headers):
        resp = await e2e_client.post(
            "/api/v1/chat",
            json={"message": ""},
            headers=api_headers,
        )
        assert resp.status_code in (200, 422)

    async def test_chat_missing_message(self, e2e_client, api_headers):
        resp = await e2e_client.post(
            "/api/v1/chat",
            json={},
            headers=api_headers,
        )
        assert resp.status_code == 422

    async def test_chat_with_session_id(self, e2e_client, api_headers):
        resp = await e2e_client.post(
            "/api/v1/chat",
            json={"message": "hello", "session_id": "test-session-123"},
            headers=api_headers,
        )
        assert resp.status_code == 200
