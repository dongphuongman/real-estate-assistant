from fastapi.testclient import TestClient

from api.dependencies import get_knowledge_store
from api.main import app
from vector_store.knowledge_store import KnowledgeStore

client = TestClient(app)

def _make_store(monkeypatch, tmp_path) -> KnowledgeStore:
    monkeypatch.setattr("vector_store.knowledge_store._create_embeddings", lambda: None)
    return KnowledgeStore(persist_directory=str(tmp_path), collection_name="knowledge-test")

def _override_store(store):
    app.dependency_overrides[get_knowledge_store] = lambda: store


def test_rag_upload_text_success(monkeypatch, tmp_path):
    store = _make_store(monkeypatch, tmp_path)
    _override_store(store)
    try:
        files = {"files": ("note.md", b"# Title\n\nHello world", "text/markdown")}
        resp = client.post("/api/v1/rag/upload", files=files, headers={"X-API-Key": "dev-secret-key"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["chunks_indexed"] > 0
        assert data["errors"] == []
    finally:
        app.dependency_overrides.pop(get_knowledge_store, None)



def test_rag_upload_unsupported_type(monkeypatch, tmp_path):
    store = _make_store(monkeypatch, tmp_path)
    _override_store(store)

    try:
        files = {"files": ("doc.pdf", b"%PDF-", "application/pdf")}
        resp = client.post("/api/v1/rag/upload", files=files, headers={"X-API-Key": "dev-secret-key"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["chunks_indexed"] == 0
        assert any("Unsupported file type" in e for e in data["errors"])
    finally:
        app.dependency_overrides.pop(get_knowledge_store, None)

def test_rag_upload_no_files(monkeypatch, tmp_path):
    store = _make_store(monkeypatch, tmp_path)
    _override_store(store)
    try:
        resp = client.post("/api/v1/rag/upload", headers={"X-API-Key": "dev-secret-key"})
        assert resp.status_code == 422  # FastAPI validates form-data presence
    finally:
        app.dependency_overrides.pop(get_knowledge_store, None)

def test_rag_upload_store_unavailable(monkeypatch):
    _override_store(None)
    try:
        files = {"files": ("note.md", b"Hello", "text/markdown")}
        resp = client.post("/api/v1/rag/upload", files=files, headers={"X-API-Key": "dev-secret-key"})
        assert resp.status_code == 503
        assert resp.json()["detail"] == "Knowledge store is not available"
    finally:
        app.dependency_overrides.pop(get_knowledge_store, None)


def test_rag_qa_returns_citations(monkeypatch, tmp_path):
    store = _make_store(monkeypatch, tmp_path)
    _override_store(store)

    try:
        store.ingest_text("The capital of Poland is Warsaw.", source="facts.md")

        resp = client.post(
            "/api/v1/rag/qa",
            params={"question": "capital Poland", "top_k": 3},
            headers={"X-API-Key": "dev-secret-key"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data["answer"], str)
        assert data["citations"] != []
    finally:
        app.dependency_overrides.pop(get_knowledge_store, None)

def test_rag_qa_no_docs(monkeypatch, tmp_path):
    store = _make_store(monkeypatch, tmp_path)
    _override_store(store)
    try:
        resp = client.post(
            "/api/v1/rag/qa",
            params={"question": "unknown", "top_k": 2},
            headers={"X-API-Key": "dev-secret-key"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["answer"] == ""
        assert data["citations"] == []
    finally:
        app.dependency_overrides.pop(get_knowledge_store, None)

def test_rag_qa_llm_unavailable(monkeypatch, tmp_path):
    store = _make_store(monkeypatch, tmp_path)
    _override_store(store)
    # Force get_llm to fail
    monkeypatch.setattr("api.routers.rag.get_llm", lambda: (_ for _ in ()).throw(RuntimeError("no llm")))
    try:
        store.ingest_text("The answer is here", source="s.md")
        resp = client.post(
            "/api/v1/rag/qa",
            params={"question": "answer", "top_k": 1},
            headers={"X-API-Key": "dev-secret-key"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data["answer"], str)
        assert data["citations"] != []
    finally:
        app.dependency_overrides.pop(get_knowledge_store, None)


def test_rag_upload_ingest_exception_is_reported(monkeypatch, tmp_path):
    store = _make_store(monkeypatch, tmp_path)
    _override_store(store)
    monkeypatch.setattr(store, "ingest_text", lambda text, source: (_ for _ in ()).throw(RuntimeError("boom")))

    try:
        files = {"files": ("note.md", b"Hello", "text/markdown")}
        resp = client.post("/api/v1/rag/upload", files=files, headers={"X-API-Key": "dev-secret-key"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["chunks_indexed"] == 0
        assert any("boom" in e for e in data["errors"])
    finally:
        app.dependency_overrides.pop(get_knowledge_store, None)


def test_rag_qa_store_unavailable_returns_503(monkeypatch):
    _override_store(None)
    try:
        resp = client.post(
            "/api/v1/rag/qa",
            params={"question": "hi", "top_k": 1},
            headers={"X-API-Key": "dev-secret-key"},
        )
        assert resp.status_code == 503
        assert resp.json()["detail"] == "Knowledge store is not available"
    finally:
        app.dependency_overrides.pop(get_knowledge_store, None)


def test_rag_qa_lazy_llm_success(monkeypatch, tmp_path):
    store = _make_store(monkeypatch, tmp_path)
    _override_store(store)

    class _Msg:
        def __init__(self, content: str):
            self.content = content

    class _Llm:
        def invoke(self, prompt: str):
            assert "context" in prompt.lower()
            return _Msg("ok")

    monkeypatch.setattr("api.routers.rag.get_llm", lambda: _Llm())
    try:
        store.ingest_text("The capital of Poland is Warsaw.", source="facts.md")
        resp = client.post(
            "/api/v1/rag/qa",
            params={"question": "capital poland", "top_k": 1},
            headers={"X-API-Key": "dev-secret-key"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["answer"] == "ok"
        assert data["citations"] != []
    finally:
        app.dependency_overrides.pop(get_knowledge_store, None)

def test_rag_qa_empty_question(monkeypatch, tmp_path):
    store = _make_store(monkeypatch, tmp_path)
    _override_store(store)
    try:
        resp = client.post(
            "/api/v1/rag/qa",
            params={"question": "   "},
            headers={"X-API-Key": "dev-secret-key"},
        )
        assert resp.status_code == 400
    finally:
        app.dependency_overrides.pop(get_knowledge_store, None)
