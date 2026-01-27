import asyncio
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from api.dependencies import get_llm, get_vector_store
from api.main import app
from config.settings import get_settings

client = TestClient(app)


def _make_sse_agent(chunks):
    class _Agent:
        async def astream_query(self, message: str):
            for c in chunks:
                await asyncio.sleep(0)
                yield c
    return _Agent()


def test_chat_sse_stream_success():
    settings = get_settings()
    key = settings.api_access_key

    mock_llm = MagicMock()
    mock_store = MagicMock()
    mock_store.get_retriever.return_value = MagicMock()
    app.dependency_overrides[get_llm] = lambda: mock_llm
    app.dependency_overrides[get_vector_store] = lambda: mock_store

    agent = _make_sse_agent(["{\"content\": \"chunk-1\"}", "{\"content\": \"chunk-2\"}"])

    with patch("api.routers.chat.create_hybrid_agent", return_value=agent):
        with client.stream(
            "POST",
            "/api/v1/chat",
            json={"message": "Hello", "stream": True},
            headers={"X-API-Key": key},
        ) as r:
            assert r.status_code == 200
            ct = r.headers.get("content-type", "")
            assert ct.startswith("text/event-stream")
            body = b"".join(list(r.iter_bytes())).decode("utf-8")
            assert "data: {\"content\": \"chunk-1\"}" in body
            assert "data: {\"content\": \"chunk-2\"}" in body
            assert "event: meta" in body
            assert "\"sources\"" in body
            assert "data: [DONE]" in body

    app.dependency_overrides = {}


def test_chat_sse_includes_request_id_in_meta_event():
    """Test that request_id is included in SSE meta events for correlation."""
    settings = get_settings()
    key = settings.api_access_key
    test_request_id = "test-req-12345"

    mock_llm = MagicMock()
    mock_store = MagicMock()
    mock_store.get_retriever.return_value = MagicMock()
    app.dependency_overrides[get_llm] = lambda: mock_llm
    app.dependency_overrides[get_vector_store] = lambda: mock_store

    agent = _make_sse_agent([])

    with patch("api.routers.chat.create_hybrid_agent", return_value=agent):
        with client.stream(
            "POST",
            "/api/v1/chat",
            json={"message": "Hello", "stream": True},
            headers={"X-API-Key": key, "X-Request-ID": test_request_id},
        ) as r:
            assert r.status_code == 200
            body = b"".join(list(r.iter_bytes())).decode("utf-8")
            # Check that request_id is in meta event
            assert "event: meta" in body
            assert f"\"request_id\": \"{test_request_id}\"" in body

    app.dependency_overrides = {}


def test_chat_sse_error_event_on_streaming_failure():
    """Test that streaming failures send explicit error events with request_id."""
    settings = get_settings()
    key = settings.api_access_key
    test_request_id = "test-req-failed"

    class _FailingAgent:
        async def astream_query(self, message: str):
            await asyncio.sleep(0)
            raise RuntimeError("streaming failed")

    mock_llm = MagicMock()
    mock_store = MagicMock()
    mock_store.get_retriever.return_value = MagicMock()
    app.dependency_overrides[get_llm] = lambda: mock_llm
    app.dependency_overrides[get_vector_store] = lambda: mock_store

    agent = _FailingAgent()

    with patch("api.routers.chat.create_hybrid_agent", return_value=agent):
        with client.stream(
            "POST",
            "/api/v1/chat",
            json={"message": "Hello", "stream": True},
            headers={"X-API-Key": key, "X-Request-ID": test_request_id},
        ) as r:
            assert r.status_code == 200
            body = b"".join(list(r.iter_bytes())).decode("utf-8")
            # Check that error event is sent with request_id
            assert "event: error" in body
            assert f"\"request_id\": \"{test_request_id}\"" in body
            assert "streaming failed" in body
            # Stream should still terminate properly
            assert "data: [DONE]" in body

    app.dependency_overrides = {}

