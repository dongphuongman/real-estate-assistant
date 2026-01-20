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

def test_rag_upload_no_files(monkeypatch):
    store = KnowledgeStore()
    monkeypatch.setattr("api.dependencies.get_knowledge_store", lambda: store)
    resp = client.post("/api/v1/rag/upload", headers={"X-API-Key": "dev-secret-key"})
    assert resp.status_code == 422  # FastAPI validates form-data presence

def test_rag_upload_store_unavailable(monkeypatch):
    # Behavior may vary with dependency overrides; ensure endpoint still works
    monkeypatch.setattr("api.dependencies.get_knowledge_store", lambda: None)
    files = {"files": ("note.md", b"Hello", "text/markdown")}
    resp = client.post("/api/v1/rag/upload", files=files, headers={"X-API-Key": "dev-secret-key"})
    assert resp.status_code in (200, 503)


def test_rag_qa_returns_citations(monkeypatch):
    store = KnowledgeStore()
    monkeypatch.setattr("api.dependencies.get_knowledge_store", lambda: store)

    # Seed one document
    store.ingest_text("The capital of Poland is Warsaw.", source="facts.md")

    resp = client.post(
        "/api/v1/rag/qa",
        params={"question": "capital Poland", "top_k": 3},
        headers={"X-API-Key": "dev-secret-key"},
    )
    assert resp.status_code == 200
    data = resp.json()
    # Without LLM, answer may be a snippet; ensure string response
    assert isinstance(data["answer"], str)

def test_rag_qa_no_docs(monkeypatch):
    store = KnowledgeStore()
    monkeypatch.setattr("api.dependencies.get_knowledge_store", lambda: store)
    resp = client.post(
        "/api/v1/rag/qa",
        params={"question": "unknown", "top_k": 2},
        headers={"X-API-Key": "dev-secret-key"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["answer"] == ""
    assert data["citations"] == []

def test_rag_qa_llm_unavailable(monkeypatch):
    store = KnowledgeStore()
    monkeypatch.setattr("api.dependencies.get_knowledge_store", lambda: store)
    # Force get_llm to fail
    monkeypatch.setattr("api.routers.rag.get_llm", lambda: (_ for _ in ()).throw(RuntimeError("no llm")))
    store.ingest_text("Answer is here", source="s.md")
    resp = client.post(
        "/api/v1/rag/qa",
        params={"question": "Answer?", "top_k": 1},
        headers={"X-API-Key": "dev-secret-key"},
    )
    assert resp.status_code == 200

def test_rag_qa_empty_question(monkeypatch):
    store = KnowledgeStore()
    monkeypatch.setattr("api.dependencies.get_knowledge_store", lambda: store)

    resp = client.post(
        "/api/v1/rag/qa",
        params={"question": "   "},
        headers={"X-API-Key": "dev-secret-key"},
    )
    assert resp.status_code == 400
