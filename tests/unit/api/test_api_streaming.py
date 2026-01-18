from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from api.dependencies import get_llm, get_vector_store
from api.main import app

client = TestClient(app)

@pytest.fixture
def valid_headers():
    return {"X-API-Key": "dev-secret-key"}

def test_chat_streaming(valid_headers):
    mock_agent = MagicMock()
    
    async def mock_stream(query):
        yield '{"content": "Hello"}'
        yield '{"content": " World"}'
        
    mock_agent.astream_query = mock_stream
    
    mock_store = MagicMock()
    mock_store.get_retriever.return_value = MagicMock()
    app.dependency_overrides[get_vector_store] = lambda: mock_store
    app.dependency_overrides[get_llm] = lambda: MagicMock()
    
    try:
        payload = {
            "message": "Hello",
            "stream": True
        }
        
        with patch("api.routers.chat.create_hybrid_agent", return_value=mock_agent):
            response = client.post(
                "/api/v1/chat",
                json=payload,
                headers=valid_headers
            )
        
        assert response.status_code == 200
        # Media type can include charset
        assert "text/event-stream" in response.headers["content-type"]
        
        content = response.text
        # Check for SSE format
        assert 'data: {"content": "Hello"}\n\n' in content
        assert 'data: {"content": " World"}\n\n' in content
        assert 'data: [DONE]\n\n' in content
        
    finally:
        app.dependency_overrides = {}

def test_chat_streaming_unauthorized():
    payload = {"message": "Hello", "stream": True}
    response = client.post("/api/v1/chat", json=payload)
    assert response.status_code == 401
