from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from api.dependencies import get_vector_store
from api.main import app
from data.schemas import Property, PropertyCollection

client = TestClient(app)

@pytest.fixture
def valid_headers():
    return {"X-API-Key": "dev-secret-key"}

@pytest.fixture
def mock_vector_store():
    store = MagicMock()
    return store

def test_admin_health_check(valid_headers, mock_vector_store):
    app.dependency_overrides[get_vector_store] = lambda: mock_vector_store
    
    # Mock load_collection to return something (healthy)
    with patch("api.routers.admin.load_collection") as mock_load:
        mock_load.return_value = PropertyCollection(properties=[], total_count=0)
        
        response = client.get("/api/v1/admin/health", headers=valid_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
    
    app.dependency_overrides = {}

def test_admin_ingest(valid_headers):
    # Mock DataLoaderCsv
    with patch("api.routers.admin.DataLoaderCsv") as MockLoader, \
         patch("api.routers.admin.save_collection") as mock_save:
        
        mock_instance = MockLoader.return_value
        # Mock load_df
        mock_instance.load_df.return_value = pd.DataFrame()
        # Mock load_format_df to return a valid DF with property columns
        mock_instance.load_format_df.return_value = pd.DataFrame([{
            "id": "1",
            "title": "Test Property",
            "price": 100000,
            "city": "Test City",
            "rooms": 2,
            "area_sqm": 50
        }])
        
        payload = {"file_urls": ["http://example.com/data.csv"]}
        response = client.post("/api/v1/admin/ingest", json=payload, headers=valid_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Ingestion successful"
        assert data["properties_processed"] == 1
        
        mock_save.assert_called_once()

def test_admin_reindex(valid_headers, mock_vector_store):
    app.dependency_overrides[get_vector_store] = lambda: mock_vector_store
    
    # Mock load_collection to return data
    with patch("api.routers.admin.load_collection") as mock_load:
        mock_load.return_value = PropertyCollection(
            properties=[Property(id="1", title="Test Property", price=100, city="City", rooms=1)], 
            total_count=1
        )
        
        response = client.post("/api/v1/admin/reindex", json={}, headers=valid_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Reindexing successful"
        assert data["count"] == 1
        
        mock_vector_store.add_documents.assert_called_once()
        
    app.dependency_overrides = {}

def test_admin_endpoints_unauthorized():
    response = client.get("/api/v1/admin/health")
    assert response.status_code == 401
    
    response = client.post("/api/v1/admin/ingest", json={})
    assert response.status_code == 401
    
    response = client.post("/api/v1/admin/reindex", json={})
    assert response.status_code == 401


def test_admin_reindex_no_cache_returns_404(valid_headers, mock_vector_store):
    app.dependency_overrides[get_vector_store] = lambda: mock_vector_store
    with patch("api.routers.admin.load_collection") as mock_load:
        mock_load.return_value = None
        response = client.post("/api/v1/admin/reindex", json={}, headers=valid_headers)
        assert response.status_code == 404
        assert "Run ingestion first" in response.json()["detail"]
    app.dependency_overrides = {}


def test_admin_ingest_no_urls_returns_400(valid_headers, monkeypatch):
    import api.routers.admin as admin_router
    # Ensure no defaults configured
    monkeypatch.setattr(admin_router, "settings", SimpleNamespace(default_datasets=[]))
    response = client.post("/api/v1/admin/ingest", json={"file_urls": []}, headers=valid_headers)
    assert response.status_code == 400
    assert "No URLs provided" in response.json()["detail"]
