from unittest.mock import MagicMock, patch

import pandas as pd
from fastapi.testclient import TestClient

from api.dependencies import get_vector_store
from api.main import app

client = TestClient(app)

HEADERS = {"X-API-Key": "test-key"}


@patch("api.routers.admin.DataLoaderCsv")
@patch("api.routers.admin.save_collection")
@patch("api.routers.admin.settings")
@patch("api.auth.get_settings")
def test_admin_ingest_uses_defaults_and_returns_success(
    mock_get_settings,
    mock_settings,
    mock_save_collection,
    mock_loader_cls,
):
    mock_get_settings.return_value = MagicMock(api_access_key="test-key")
    mock_settings.default_datasets = ["http://example.com/test.csv"]

    loader = MagicMock()
    loader.load_df.return_value = pd.DataFrame([{"city": "Warsaw"}, {"bad": "row"}])
    loader.load_format_df.side_effect = lambda df: df
    mock_loader_cls.return_value = loader

    resp = client.post("/api/v1/admin/ingest", json={}, headers=HEADERS)
    assert resp.status_code == 200
    data = resp.json()
    assert data["message"] == "Ingestion successful"
    assert data["properties_processed"] == 1
    assert data["errors"] == []
    assert mock_save_collection.called


@patch("api.routers.admin.DataLoaderCsv")
@patch("api.routers.admin.settings")
@patch("api.auth.get_settings")
def test_admin_ingest_returns_400_when_no_urls_and_no_defaults(
    mock_get_settings, mock_settings, mock_loader_cls
):
    mock_get_settings.return_value = MagicMock(api_access_key="test-key")
    mock_settings.default_datasets = []

    resp = client.post("/api/v1/admin/ingest", json={"file_urls": []}, headers=HEADERS)
    assert resp.status_code == 400
    assert resp.json()["detail"] == "No URLs provided and no defaults configured"
    assert not mock_loader_cls.called


@patch("api.routers.admin.DataLoaderCsv")
@patch("api.routers.admin.save_collection")
@patch("api.routers.admin.settings")
@patch("api.auth.get_settings")
def test_admin_ingest_returns_500_when_no_properties_loaded(
    mock_get_settings,
    mock_settings,
    mock_save_collection,
    mock_loader_cls,
):
    mock_get_settings.return_value = MagicMock(api_access_key="test-key")
    mock_settings.default_datasets = ["http://example.com/empty.csv"]

    loader = MagicMock()
    loader.load_df.return_value = pd.DataFrame([{"bad": "row"}])
    loader.load_format_df.side_effect = lambda df: df
    mock_loader_cls.return_value = loader

    resp = client.post("/api/v1/admin/ingest", json={}, headers=HEADERS)
    assert resp.status_code == 500
    assert resp.json()["detail"] == "No properties could be loaded"
    assert not mock_save_collection.called


@patch("api.routers.admin.DataLoaderCsv")
@patch("api.routers.admin.save_collection")
@patch("api.routers.admin.settings")
@patch("api.auth.get_settings")
def test_admin_ingest_returns_errors_when_some_urls_fail(
    mock_get_settings,
    mock_settings,
    mock_save_collection,
    mock_loader_cls,
):
    mock_get_settings.return_value = MagicMock(api_access_key="test-key")
    urls = ["http://example.com/ok.csv", "http://example.com/bad.csv"]
    mock_settings.default_datasets = urls

    ok_loader = MagicMock()
    ok_loader.load_df.return_value = pd.DataFrame([{"city": "Warsaw"}])
    ok_loader.load_format_df.side_effect = lambda df: df

    def _loader(url: str):
        if url.endswith("bad.csv"):
            raise RuntimeError("network down")
        return ok_loader

    mock_loader_cls.side_effect = _loader

    resp = client.post("/api/v1/admin/ingest", json={}, headers=HEADERS)
    assert resp.status_code == 200
    data = resp.json()
    assert data["properties_processed"] == 1
    assert len(data["errors"]) == 1
    assert "Failed to load" in data["errors"][0]
    assert mock_save_collection.called


@patch("api.routers.admin.DataLoaderCsv")
@patch("api.routers.admin.save_collection")
@patch("api.routers.admin.settings")
@patch("api.auth.get_settings")
def test_admin_ingest_returns_500_on_unhandled_exception(
    mock_get_settings,
    mock_settings,
    mock_save_collection,
    mock_loader_cls,
):
    mock_get_settings.return_value = MagicMock(api_access_key="test-key")
    mock_settings.default_datasets = ["http://example.com/test.csv"]

    loader = MagicMock()
    loader.load_df.return_value = pd.DataFrame([{"city": "Warsaw"}])
    loader.load_format_df.side_effect = lambda df: df
    mock_loader_cls.return_value = loader
    mock_save_collection.side_effect = RuntimeError("disk full")

    resp = client.post("/api/v1/admin/ingest", json={}, headers=HEADERS)
    assert resp.status_code == 500
    assert resp.json()["detail"] == "disk full"


@patch("api.routers.admin.load_collection")
@patch("api.auth.get_settings")
def test_admin_reindex_returns_404_when_no_cache(mock_get_settings, mock_load_collection):
    mock_get_settings.return_value = MagicMock(api_access_key="test-key")
    mock_load_collection.return_value = None

    resp = client.post("/api/v1/admin/reindex", json={}, headers=HEADERS)
    assert resp.status_code == 404
    assert resp.json()["detail"] == "No data in cache. Run ingestion first."


@patch("api.routers.admin.load_collection")
@patch("api.auth.get_settings")
def test_admin_reindex_returns_503_when_store_unavailable(mock_get_settings, mock_load_collection):
    mock_get_settings.return_value = MagicMock(api_access_key="test-key")
    mock_load_collection.return_value = MagicMock(properties=[MagicMock()])
    app.dependency_overrides[get_vector_store] = lambda: None

    try:
        resp = client.post("/api/v1/admin/reindex", json={}, headers=HEADERS)
    finally:
        app.dependency_overrides.pop(get_vector_store, None)

    assert resp.status_code == 503
    assert resp.json()["detail"] == "Vector store unavailable"


@patch("api.routers.admin.load_collection")
@patch("api.auth.get_settings")
def test_admin_reindex_success(mock_get_settings, mock_load_collection):
    mock_get_settings.return_value = MagicMock(api_access_key="test-key")
    mock_load_collection.return_value = MagicMock(properties=[MagicMock(), MagicMock()])
    store = MagicMock()
    app.dependency_overrides[get_vector_store] = lambda: store

    try:
        resp = client.post("/api/v1/admin/reindex", json={}, headers=HEADERS)
    finally:
        app.dependency_overrides.pop(get_vector_store, None)

    assert resp.status_code == 200
    data = resp.json()
    assert data["message"] == "Reindexing successful"
    assert data["count"] == 2
    store.add_documents.assert_called_once()


@patch("api.routers.admin.load_collection")
@patch("api.auth.get_settings")
def test_admin_reindex_returns_500_when_store_fails(mock_get_settings, mock_load_collection):
    mock_get_settings.return_value = MagicMock(api_access_key="test-key")
    mock_load_collection.return_value = MagicMock(properties=[MagicMock()])
    store = MagicMock()
    store.add_documents.side_effect = RuntimeError("boom")
    app.dependency_overrides[get_vector_store] = lambda: store

    try:
        resp = client.post("/api/v1/admin/reindex", json={}, headers=HEADERS)
    finally:
        app.dependency_overrides.pop(get_vector_store, None)

    assert resp.status_code == 500
    assert resp.json()["detail"] == "boom"


@patch("api.routers.admin.load_collection")
@patch("api.auth.get_settings")
def test_admin_health_degraded_when_no_cache_or_store(mock_get_settings, mock_load_collection):
    mock_get_settings.return_value = MagicMock(api_access_key="test-key")
    mock_load_collection.return_value = None
    app.dependency_overrides[get_vector_store] = lambda: None

    try:
        resp = client.get("/api/v1/admin/health", headers=HEADERS)
    finally:
        app.dependency_overrides.pop(get_vector_store, None)

    assert resp.status_code == 200
    assert resp.json()["status"] == "degraded (vector store unavailable)"


@patch("api.routers.admin.load_collection")
@patch("api.auth.get_settings")
def test_admin_health_degraded_when_no_cache(mock_get_settings, mock_load_collection):
    mock_get_settings.return_value = MagicMock(api_access_key="test-key")
    mock_load_collection.return_value = None
    app.dependency_overrides[get_vector_store] = lambda: MagicMock()

    try:
        resp = client.get("/api/v1/admin/health", headers=HEADERS)
    finally:
        app.dependency_overrides.pop(get_vector_store, None)

    assert resp.status_code == 200
    assert resp.json()["status"] == "degraded (no data cache)"


@patch("api.auth.get_settings")
def test_admin_metrics_returns_app_state_metrics(mock_get_settings):
    mock_get_settings.return_value = MagicMock(api_access_key="test-key")
    old_metrics = getattr(app.state, "metrics", None)
    app.state.metrics = {"GET /api/v1/verify-auth": 2}
    try:
        resp = client.get("/api/v1/admin/metrics", headers=HEADERS)
        assert resp.status_code == 200
        assert resp.json() == {"GET /api/v1/verify-auth": 2}
    finally:
        app.state.metrics = old_metrics if old_metrics is not None else {}


@patch("api.auth.get_settings")
def test_admin_metrics_returns_500_on_invalid_metrics(mock_get_settings):
    mock_get_settings.return_value = MagicMock(api_access_key="test-key")
    old_metrics = getattr(app.state, "metrics", None)

    class _Metrics:
        def __init__(self):
            self._d: dict[str, int] = {}

        def get(self, key, default=0):
            return self._d.get(key, default)

        def __setitem__(self, key, value):
            self._d[key] = value

        def __iter__(self):
            raise TypeError("not iterable")

    app.state.metrics = _Metrics()
    try:
        resp = client.get("/api/v1/admin/metrics", headers=HEADERS)
        assert resp.status_code == 500
        assert resp.json()["detail"]
    finally:
        app.state.metrics = old_metrics if old_metrics is not None else {}
