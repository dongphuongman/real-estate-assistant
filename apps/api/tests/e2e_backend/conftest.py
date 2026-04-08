"""
E2E test fixtures — full app lifecycle with real dependency wiring.

These tests exercise the complete request path:
  Client → Auth Middleware → Router → Service → Response
"""

import os
from collections.abc import AsyncGenerator

import pytest
from httpx import ASGITransport, AsyncClient

# Ensure test environment before any app imports
os.environ.setdefault("ENVIRONMENT", "test")
os.environ.setdefault("API_ACCESS_KEY", "test-e2e-key-12345")
os.environ.setdefault("ENABLE_JWT_AUTH", "false")

API_KEY = os.environ["API_ACCESS_KEY"]


@pytest.fixture(scope="session")
def anyio_backend():
    return "asyncio"


@pytest.fixture(scope="session")
async def e2e_client() -> AsyncGenerator[AsyncClient, None]:
    """
    Session-scoped E2E client with the real app.

    Overrides only external services (LLM, vector store) to avoid
    hitting real APIs while keeping auth, middleware, and routing intact.
    """
    from unittest.mock import AsyncMock, MagicMock

    from api.dependencies import get_llm, get_optional_llm_with_details, get_vector_store
    from api.main import app

    # Mock vector store
    mock_store = MagicMock()
    mock_store.similarity_search_with_score.return_value = []
    mock_store.get_stats.return_value = {"documents": 0}

    # Mock LLM
    mock_llm = MagicMock()
    mock_msg = MagicMock()
    mock_msg.content = "E2E test response"
    mock_llm.invoke.return_value = mock_msg
    mock_llm.astream = AsyncMock()

    app.dependency_overrides[get_vector_store] = lambda: mock_store
    app.dependency_overrides[get_llm] = lambda: mock_llm
    app.dependency_overrides[get_optional_llm_with_details] = lambda: (
        mock_llm,
        "mock",
        "mock-model",
    )

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client

    app.dependency_overrides.clear()


@pytest.fixture
def api_headers() -> dict[str, str]:
    """Headers with valid API key."""
    return {"X-API-Key": API_KEY}
