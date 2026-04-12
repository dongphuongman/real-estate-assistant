"""Unit tests for AnomalyService."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from services.anomaly_service import AnomalyService


def _make_anomaly_repo():
    """Create a mock AnomalyRepository."""
    repo = AsyncMock()
    # Ensure get_by_id is a proper AsyncMock (not auto-generated with spec issues)
    repo.get_by_id = AsyncMock()
    return repo


def _make_snapshot_repo():
    """Create a mock PriceSnapshotRepository."""
    return AsyncMock()


def _make_alert_manager():
    """Create a mock AlertManager."""
    return MagicMock()


class TestRunDailyAnalysis:
    """Tests for run_daily_analysis method."""

    @pytest.mark.asyncio
    async def test_returns_counts_with_no_anomalies(self):
        """Returns zero counts when no anomalies detected."""
        anomaly_repo = _make_anomaly_repo()
        snapshot_repo = _make_snapshot_repo()
        snapshot_repo.get_snapshots_in_period.return_value = []

        service = AnomalyService(anomaly_repo, snapshot_repo)
        result = await service.run_daily_analysis()

        # price_anomalies and volume_anomalies are lists (not counts)
        assert result["price_anomalies"] == []
        assert result["volume_anomalies"] == []
        assert result["total_anomalies"] == 0
        assert result["alerts_sent"] == 0
        assert result["errors"] == []

    @pytest.mark.asyncio
    async def test_detects_price_anomalies(self):
        """Detects and stores price anomalies from snapshots."""
        anomaly_repo = _make_anomaly_repo()
        snapshot_repo = _make_snapshot_repo()

        # Create 12 snapshots for one property (above minimum of 10)
        snapshots = []
        for i in range(12):
            snap = MagicMock()
            snap.property_id = "prop-001"
            snap.recorded_at = datetime(2025, 1, i + 1, tzinfo=timezone.utc)
            snapshots.append(snap)

        snapshot_repo.get_snapshots_in_period.return_value = snapshots

        # Mock the detector to return one anomaly
        mock_detected = MagicMock()
        mock_detected.anomaly_type.value = "price_spike"
        mock_detected.severity.value = "high"
        mock_detected.scope_type.value = "property"
        mock_detected.scope_id = "prop-001"
        mock_detected.algorithm = "zscore"
        mock_detected.threshold_used = 2.0
        mock_detected.metric_name = "price"
        mock_detected.expected_value = 500000
        mock_detected.actual_value = 700000
        mock_detected.deviation_percent = 40.0
        mock_detected.z_score = 3.1
        mock_detected.context = {}

        db_anomaly = MagicMock()
        db_anomaly.id = "anom-001"
        db_anomaly.anomaly_type = "price_spike"
        db_anomaly.severity = "high"
        db_anomaly.scope_id = "prop-001"
        anomaly_repo.create.return_value = db_anomaly

        service = AnomalyService(anomaly_repo, snapshot_repo)
        with patch.object(service.detector, "detect_price_anomalies", return_value=[mock_detected]):
            result = await service.run_daily_analysis()

        # price_anomalies is a list of dicts
        assert len(result["price_anomalies"]) == 1
        assert result["total_anomalies"] == 1
        anomaly_repo.create.assert_called_once()

    @pytest.mark.asyncio
    async def test_sends_alerts_for_high_severity(self):
        """Sends alerts when high/critical severity anomalies are detected."""
        anomaly_repo = _make_anomaly_repo()
        snapshot_repo = _make_snapshot_repo()
        alert_manager = _make_alert_manager()
        alert_manager.queue_alert = MagicMock()

        snapshots = []
        for i in range(12):
            snap = MagicMock()
            snap.property_id = "prop-001"
            snap.recorded_at = datetime(2025, 1, i + 1, tzinfo=timezone.utc)
            snapshots.append(snap)
        snapshot_repo.get_snapshots_in_period.return_value = snapshots

        mock_detected = MagicMock()
        mock_detected.anomaly_type.value = "price_spike"
        mock_detected.severity.value = "critical"
        mock_detected.scope_type.value = "property"
        mock_detected.scope_id = "prop-001"
        mock_detected.algorithm = "zscore"
        mock_detected.threshold_used = 2.0
        mock_detected.metric_name = "price"
        mock_detected.expected_value = 500000
        mock_detected.actual_value = 900000
        mock_detected.deviation_percent = 80.0
        mock_detected.z_score = 4.5
        mock_detected.context = {}

        db_anomaly = MagicMock()
        db_anomaly.id = "anom-crit-001"
        db_anomaly.anomaly_type = "price_spike"
        db_anomaly.severity = "critical"
        db_anomaly.scope_id = "prop-001"
        anomaly_repo.create.return_value = db_anomaly
        anomaly_repo.mark_alert_sent = AsyncMock()

        service = AnomalyService(anomaly_repo, snapshot_repo, alert_manager)
        with patch.object(service.detector, "detect_price_anomalies", return_value=[mock_detected]):
            result = await service.run_daily_analysis()

        assert result["alerts_sent"] == 1
        alert_manager.queue_alert.assert_called_once()
        anomaly_repo.mark_alert_sent.assert_called_once_with("anom-crit-001")

    @pytest.mark.asyncio
    async def test_no_alerts_without_alert_manager(self):
        """Does not attempt alerts when alert_manager is None."""
        anomaly_repo = _make_anomaly_repo()
        snapshot_repo = _make_snapshot_repo()
        snapshot_repo.get_snapshots_in_period.return_value = []

        service = AnomalyService(anomaly_repo, snapshot_repo, alert_manager=None)
        result = await service.run_daily_analysis()

        assert result["alerts_sent"] == 0

    @pytest.mark.asyncio
    async def test_handles_error_gracefully(self):
        """Appends error message when exception occurs."""
        anomaly_repo = _make_anomaly_repo()
        snapshot_repo = _make_snapshot_repo()
        snapshot_repo.get_snapshots_in_period.side_effect = Exception("DB connection failed")

        service = AnomalyService(anomaly_repo, snapshot_repo)
        result = await service.run_daily_analysis()

        assert len(result["errors"]) == 1
        assert "DB connection failed" in result["errors"][0]

    @pytest.mark.asyncio
    async def test_skips_properties_with_fewer_than_10_snapshots(self):
        """Skips anomaly detection for properties with < 10 snapshots."""
        anomaly_repo = _make_anomaly_repo()
        snapshot_repo = _make_snapshot_repo()

        # Only 5 snapshots (below minimum of 10)
        snapshots = []
        for i in range(5):
            snap = MagicMock()
            snap.property_id = "prop-001"
            snap.recorded_at = datetime(2025, 1, i + 1, tzinfo=timezone.utc)
            snapshots.append(snap)
        snapshot_repo.get_snapshots_in_period.return_value = snapshots

        service = AnomalyService(anomaly_repo, snapshot_repo)
        result = await service.run_daily_analysis()

        assert result["price_anomalies"] == []
        anomaly_repo.create.assert_not_called()


class TestGetAnomalies:
    """Tests for get_anomalies method."""

    @pytest.mark.asyncio
    async def test_returns_anomaly_list_response(self):
        """Returns AnomalyListResponse with anomalies."""
        anomaly_repo = _make_anomaly_repo()

        mock_anomaly = MagicMock()
        mock_anomaly.scope_type = "property"
        mock_anomaly.scope_id = "prop-001"
        anomaly_repo.get_recent.return_value = [mock_anomaly]

        service = AnomalyService(anomaly_repo, _make_snapshot_repo())
        with patch("services.anomaly_service.AnomalyResponse") as mock_response_cls:
            mock_response_cls.model_validate.return_value = {"id": "a1"}
            with patch("services.anomaly_service.AnomalyListResponse") as mock_list_cls:
                mock_list_cls.return_value = MagicMock()
                await service.get_anomalies(limit=10)

        anomaly_repo.get_recent.assert_called_once_with(
            limit=10, severity_filter=None, anomaly_type_filter=None
        )

    @pytest.mark.asyncio
    async def test_applies_scope_type_filter(self):
        """Filters results by scope_type when provided."""
        anomaly_repo = _make_anomaly_repo()

        prop_anomaly = MagicMock()
        prop_anomaly.scope_type = "property"
        prop_anomaly.scope_id = "prop-001"

        city_anomaly = MagicMock()
        city_anomaly.scope_type = "city"
        city_anomaly.scope_id = "Kraków"

        anomaly_repo.get_recent.return_value = [prop_anomaly, city_anomaly]

        service = AnomalyService(anomaly_repo, _make_snapshot_repo())
        with (
            patch("services.anomaly_service.AnomalyResponse") as mock_resp,
            patch("services.anomaly_service.AnomalyListResponse") as mock_list,
        ):
            mock_resp.model_validate.return_value = MagicMock()
            mock_list.return_value = MagicMock()
            await service.get_anomalies(scope_type_filter="property")

        # Only property anomaly should be converted
        assert mock_resp.model_validate.call_count == 1

    @pytest.mark.asyncio
    async def test_passes_severity_filter_to_repo(self):
        """Passes severity_filter to repository get_recent."""
        anomaly_repo = _make_anomaly_repo()
        anomaly_repo.get_recent.return_value = []

        service = AnomalyService(anomaly_repo, _make_snapshot_repo())
        with patch("services.anomaly_service.AnomalyListResponse") as mock_list:
            mock_list.return_value = MagicMock()
            await service.get_anomalies(severity_filter="high")

        anomaly_repo.get_recent.assert_called_once_with(
            limit=50, severity_filter="high", anomaly_type_filter=None
        )


class TestGetAnomalyById:
    """Tests for get_anomaly_by_id method."""

    @pytest.mark.asyncio
    async def test_returns_anomaly_dict_when_found(self):
        """Returns __dict__ of the anomaly when found."""
        anomaly_repo = _make_anomaly_repo()
        anomaly_repo.get_by_id = AsyncMock()

        # Use a simple object with __dict__ instead of MagicMock to avoid mock internals
        class FakeAnomaly:
            def __init__(self):
                self.id = "a1"
                self.anomaly_type = "price_spike"
                self.severity = "high"

        anomaly_repo.get_by_id.return_value = FakeAnomaly()

        service = AnomalyService(anomaly_repo, _make_snapshot_repo())
        result = await service.get_anomaly_by_id("a1")

        assert result["id"] == "a1"
        assert result["anomaly_type"] == "price_spike"
        assert result["severity"] == "high"

    @pytest.mark.asyncio
    async def test_returns_none_when_not_found(self):
        """Returns None when anomaly does not exist."""
        anomaly_repo = _make_anomaly_repo()
        anomaly_repo.get_by_id.return_value = None

        service = AnomalyService(anomaly_repo, _make_snapshot_repo())
        result = await service.get_anomaly_by_id("nonexistent")

        assert result is None


class TestDismissAnomaly:
    """Tests for dismiss_anomaly method."""

    @pytest.mark.asyncio
    async def test_returns_true_when_dismissed(self):
        """Returns True when anomaly exists and is dismissed."""
        anomaly_repo = _make_anomaly_repo()
        anomaly_repo.get_by_id.return_value = MagicMock()
        anomaly_repo.dismiss = AsyncMock()

        service = AnomalyService(anomaly_repo, _make_snapshot_repo())
        result = await service.dismiss_anomaly("a1", dismissed_by="admin")

        assert result is True
        anomaly_repo.dismiss.assert_called_once_with("a1", "admin")

    @pytest.mark.asyncio
    async def test_returns_false_when_not_found(self):
        """Returns False when anomaly does not exist."""
        anomaly_repo = _make_anomaly_repo()
        anomaly_repo.get_by_id.return_value = None

        service = AnomalyService(anomaly_repo, _make_snapshot_repo())
        result = await service.dismiss_anomaly("nonexistent")

        assert result is False

    @pytest.mark.asyncio
    async def test_returns_false_on_error(self):
        """Returns False when repo raises an exception."""
        anomaly_repo = _make_anomaly_repo()
        anomaly_repo.get_by_id.return_value = MagicMock()
        anomaly_repo.dismiss.side_effect = Exception("DB error")

        service = AnomalyService(anomaly_repo, _make_snapshot_repo())
        result = await service.dismiss_anomaly("a1")

        assert result is False


class TestGetAnomalyStats:
    """Tests for get_anomaly_stats method."""

    @pytest.mark.asyncio
    async def test_delegates_to_repository(self):
        """Returns stats from anomaly_repo.get_stats()."""
        anomaly_repo = _make_anomaly_repo()
        expected_stats = {"total": 42, "high": 5, "critical": 1}
        anomaly_repo.get_stats.return_value = expected_stats

        service = AnomalyService(anomaly_repo, _make_snapshot_repo())
        result = await service.get_anomaly_stats()

        assert result == expected_stats
        anomaly_repo.get_stats.assert_called_once()
