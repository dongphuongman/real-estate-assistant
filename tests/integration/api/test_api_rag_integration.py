from fastapi.testclient import TestClient

from api.main import app
from vector_store.knowledge_store import KnowledgeStore

client = TestClient(app)


def test_rag_end_to_end_text_upload_and_qa(monkeypatch):
    store = KnowledgeStore()
    monkeypatch.setattr("api.dependencies.get_knowledge_store", lambda: store)

    content = "Krakow is a city in Poland. It is known for Wawel Castle."
    files = {"files": ("guide.txt", content.encode("utf-8"), "text/plain")}
    r = client.post("/api/v1/rag/upload", files=files, headers={"X-API-Key": "dev-secret-key"})
    assert r.status_code == 200
    assert r.json()["chunks_indexed"] > 0

    q = client.post(
        "/api/v1/rag/qa",
        params={"question": "What is Krakow known for?"},
        headers={"X-API-Key": "dev-secret-key"},
    )
    assert q.status_code == 200
    payload = q.json()
    assert isinstance(payload["answer"], str)
    assert len(payload["citations"]) >= 1
