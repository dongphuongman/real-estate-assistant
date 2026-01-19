import types

import pytest
from fastapi.testclient import TestClient

from api.dependencies import get_llm, get_vector_store
from api.main import app
from api.routers import chat as chat_router


class FakeAgent:
    def __init__(self):
        self.emitted = ["{\"content\":\"Hello\"}", "{\"content\":\"World\"}"]

    async def astream_query(self, msg: str):
        for e in self.emitted:
            yield e

    def process_query(self, msg: str):
        return {"answer": "Hello World", "source_documents": []}


@pytest.fixture(autouse=True)
def _patch_agent(monkeypatch):
    monkeypatch.setattr(chat_router, "create_hybrid_agent", lambda llm, retriever, memory=None: FakeAgent())


def test_chat_sse_streams_events_and_sets_request_id_header():
    client = TestClient(app)
    app.dependency_overrides[get_llm] = lambda: object()
    app.dependency_overrides[get_vector_store] = lambda: types.SimpleNamespace(get_retriever=lambda: object())
    payload = {"message": "Hi", "stream": True}
    headers = {"X-API-Key": "dev-secret-key"}
    with client.stream("POST", "/api/v1/chat", json=payload, headers=headers) as r:
        assert r.headers.get("content-type").startswith("text/event-stream")
        req_id = r.headers.get("X-Request-ID")
        assert req_id and isinstance(req_id, str)
        chunks = list(r.iter_lines())
    # Ensure we received two events and [DONE]
    data_lines = [line for line in chunks if line]
    assert any(line.startswith("data: ") for line in data_lines)
    assert any(line.strip() == "data: [DONE]" for line in data_lines)
