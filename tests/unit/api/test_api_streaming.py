import pytest
from unittest.mock import AsyncMock, MagicMock
from fastapi.testclient import TestClient
from api.main import app
from api.dependencies import get_agent

client = TestClient(app)

@pytest.fixture
def valid_headers():
    return {"X-API-Key": "dev-secret-key"}

def test_chat_streaming(valid_headers):
    # Mock the agent
    mock_agent = MagicMock()
    
    # Mock astream_query to yield chunks
    async def mock_stream(query):
        yield '{"content": "Hello"}'
        yield '{"content": " World"}'
        
    mock_agent.astream_query = mock_stream
    
    # Override dependency
    app.dependency_overrides[get_agent] = lambda: mock_agent
    
    try:
        payload = {
            "message": "Hello",
            "stream": True
        }
        
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
