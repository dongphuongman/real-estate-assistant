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

    agent = _make_sse_agent(["data: {\"content\": \"chunk-1\"}\n\n", "data: {\"content\": \"chunk-2\"}\n\n", "data: [DONE]\n\n"])

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
            assert "data: [DONE]" in body

    app.dependency_overrides = {}
