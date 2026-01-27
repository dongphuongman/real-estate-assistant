import json
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
def test_admin_ingest_enforces_max_properties_limit(
    mock_get_settings,
    mock_settings,
    mock_save_collection,
    mock_loader_cls,
):
    mock_get_settings.return_value = MagicMock(api_access_key="test-key")
    mock_settings.max_properties = 2
    mock_settings.default_datasets = ["http://example.com/test.csv"]

    loader = MagicMock()
    # Create a DataFrame with 5 rows, but max_properties is 2
    loader.load_df.return_value = pd.DataFrame([
        {"city": "Warsaw"},
        {"city": "Krakow"},
        {"city": "Gdansk"},
        {"city": "Poznan"},
        {"city": "Wroclaw"}
    ])
    # Track rows_count passed to format_df
    format_df_calls = []
    def _format_df(df, rows_count=None):
        format_df_calls.append(rows_count)
        return df.head(rows_count) if rows_count else df
    loader.load_format_df.side_effect = _format_df
    mock_loader_cls.return_value = loader

    resp = client.post("/api/v1/admin/ingest", json={}, headers=HEADERS)
    assert resp.status_code == 200
    data = resp.json()
    # Should only process 2 properties (max_properties limit)
    assert data["properties_processed"] == 2
    # Message should indicate limit was reached
    assert "maximum property limit" in data["message"]
    # Verify rows_count was passed correctly (remaining capacity = 2 - 0 = 2)
    assert format_df_calls[0] == 2
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


@patch("api.routers.admin.platform.platform")
@patch("api.routers.admin._format_python_version")
@patch("api.routers.admin.settings")
@patch("api.auth.get_settings")
def test_admin_version_returns_expected_fields(
    mock_get_settings,
    mock_settings,
    mock_python_version,
    mock_platform,
):
    mock_get_settings.return_value = MagicMock(api_access_key="test-key")
    mock_settings.version = "9.9.9"
    mock_settings.environment = "test"
    mock_settings.app_title = "AI REA Test"
    mock_python_version.return_value = "3.12.3"
    mock_platform.return_value = "TestOS-1.0"

    resp = client.get("/api/v1/admin/version", headers=HEADERS)
    assert resp.status_code == 200
    assert resp.json() == {
        "version": "9.9.9",
        "environment": "test",
        "app_title": "AI REA Test",
        "python_version": "3.12.3",
        "platform": "TestOS-1.0",
    }


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


@patch("api.auth.get_settings")
def test_admin_notifications_stats_reads_alert_storage_and_scheduler_state(mock_get_settings, tmp_path):
    mock_get_settings.return_value = MagicMock(api_access_key="test-key")

    (tmp_path / "sent_alerts.json").write_text(
        json.dumps({"alerts": ["sent-1"], "last_updated": "2026-01-24T10:00:00"}), encoding="utf-8"
    )
    (tmp_path / "pending_alerts.json").write_text(
        json.dumps(
            {
                "alerts": [{"alert_type": "new_property", "created_at": "2026-01-24T10:00:00"}],
                "last_updated": "2026-01-24T10:00:10",
            }
        ),
        encoding="utf-8",
    )

    class _ThreadStub:
        def is_alive(self) -> bool:
            return True

    class _SchedulerStub:
        _storage_path_alerts = str(tmp_path)
        _thread = _ThreadStub()

    old_scheduler = getattr(app.state, "scheduler", None)
    app.state.scheduler = _SchedulerStub()
    try:
        resp = client.get("/api/v1/admin/notifications-stats", headers=HEADERS)
    finally:
        if old_scheduler is None:
            delattr(app.state, "scheduler")
        else:
            app.state.scheduler = old_scheduler

    assert resp.status_code == 200
    data = resp.json()
    assert data["scheduler_running"] is True
    assert data["alerts_storage_path"] == str(tmp_path)
    assert data["sent_alerts_total"] == 1
    assert data["pending_alerts_total"] == 1
    assert data["pending_alerts_by_type"]["new_property"] == 1
