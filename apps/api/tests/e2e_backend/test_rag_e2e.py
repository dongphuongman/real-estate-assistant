"""
E2E tests for the RAG (Retrieval-Augmented Generation) flow.

Tests document upload, QA, and reset flows.
"""

import pytest


@pytest.mark.asyncio
class TestRagE2E:
    """RAG endpoints — validates document upload, QA, and reset flows."""

    async def test_rag_qa_no_documents(self, e2e_client, api_headers):
        """QA with no documents indexed should return gracefully."""
        resp = await e2e_client.post(
            "/api/v1/rag/qa",
            json={"question": "What properties are available?"},
            headers=api_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "answer" in data or "citations" in data

    async def test_rag_qa_streaming(self, e2e_client, api_headers):
        """Streaming QA request should return SSE or valid response."""
        resp = await e2e_client.post(
            "/api/v1/rag/qa",
            json={"question": "test question", "stream": True},
            headers=api_headers,
        )
        assert resp.status_code == 200

    async def test_rag_reset(self, e2e_client, api_headers):
        """Reset endpoint should clear knowledge base."""
        resp = await e2e_client.post(
            "/api/v1/rag/reset",
            headers=api_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "message" in data

    async def test_rag_qa_with_top_k(self, e2e_client, api_headers):
        """QA with custom top_k should work."""
        resp = await e2e_client.post(
            "/api/v1/rag/qa",
            json={"question": "test", "top_k": 5},
            headers=api_headers,
        )
        assert resp.status_code == 200

    async def test_rag_upload_no_files(self, e2e_client, api_headers):
        """Upload with no files should return error."""
        resp = await e2e_client.post(
            "/api/v1/rag/upload",
            headers=api_headers,
        )
        assert resp.status_code in (400, 422)
