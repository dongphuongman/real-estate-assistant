from fastapi.testclient import TestClient

from api.main import app
from vector_store.knowledge_store import KnowledgeStore

client = TestClient(app)


def test_rag_upload_text_success(monkeypatch):
    # Ensure knowledge store exists
    store = KnowledgeStore()
    monkeypatch.setattr("api.dependencies.get_knowledge_store", lambda: store)

    files = {"files": ("note.md", b"# Title\n\nHello world", "text/markdown")}
    resp = client.post("/api/v1/rag/upload", files=files, headers={"X-API-Key": "dev-secret-key"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["chunks_indexed"] > 0
    assert data["errors"] == []


def test_rag_upload_unsupported_type(monkeypatch):
    store = KnowledgeStore()
    monkeypatch.setattr("api.dependencies.get_knowledge_store", lambda: store)

    files = {"files": ("doc.pdf", b"%PDF-", "application/pdf")}
    resp = client.post("/api/v1/rag/upload", files=files, headers={"X-API-Key": "dev-secret-key"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["chunks_indexed"] == 0
    assert any("Unsupported file type" in e for e in data["errors"])


def test_rag_qa_returns_citations(monkeypatch):
    store = KnowledgeStore()
    monkeypatch.setattr("api.dependencies.get_knowledge_store", lambda: store)

    # Seed one document
    store.ingest_text("The capital of Poland is Warsaw.", source="facts.md")

    resp = client.post(
        "/api/v1/rag/qa",
        params={"question": "What is the capital of Poland?", "top_k": 3},
        headers={"X-API-Key": "dev-secret-key"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "citations" in data
    assert len(data["citations"]) > 0
    # Without LLM, answer may be a snippet
    assert isinstance(data["answer"], str)


def test_rag_qa_empty_question(monkeypatch):
    store = KnowledgeStore()
    monkeypatch.setattr("api.dependencies.get_knowledge_store", lambda: store)

    resp = client.post(
        "/api/v1/rag/qa",
        params={"question": "   "},
        headers={"X-API-Key": "dev-secret-key"},
    )
    assert resp.status_code == 400
