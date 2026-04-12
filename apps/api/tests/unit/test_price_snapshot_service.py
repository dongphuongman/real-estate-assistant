"""Unit tests for PriceSnapshotService."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from services.price_snapshot_service import PriceSnapshotService


class TestCaptureAllPropertyPrices:
    """Tests for capture_all_property_prices method."""

    @pytest.mark.asyncio
    async def test_returns_empty_stats_when_no_cache(self):
        """Returns zeroed stats when load_collection returns None."""
        service = PriceSnapshotService()

        with patch("services.price_snapshot_service.load_collection", return_value=None):
            result = await service.capture_all_property_prices()

        assert result == {
            "captured": 0,
            "skipped": 0,
            "errors": [],
            "properties_checked": 0,
        }

    @pytest.mark.asyncio
    async def test_returns_empty_stats_when_cache_has_no_properties(self):
        """Returns zeroed stats when collection has empty properties list."""
        service = PriceSnapshotService()
        mock_collection = MagicMock()
        mock_collection.properties = []

        with patch("services.price_snapshot_service.load_collection", return_value=mock_collection):
            result = await service.capture_all_property_prices()

        assert result["captured"] == 0
        assert result["skipped"] == 0
        assert result["properties_checked"] == 0

    @pytest.mark.asyncio
    async def test_captures_new_property_price(self):
        """Creates a snapshot for a property with no previous price."""
        service = PriceSnapshotService()

        prop = MagicMock()
        prop.id = "prop-001"
        prop.price = 500000
        prop.area_sqm = 50
        prop.currency = "PLN"

        mock_collection = MagicMock()
        mock_collection.properties = [prop]

        mock_repo = AsyncMock()
        mock_repo.get_latest_for_property.return_value = None
        mock_repo.create = AsyncMock()

        mock_session = AsyncMock()
        mock_repo_cm = AsyncMock()
        mock_repo_cm.__aenter__ = AsyncMock(return_value=mock_session)
        mock_repo_cm.__aexit__ = AsyncMock(return_value=False)

        with (
            patch("services.price_snapshot_service.load_collection", return_value=mock_collection),
            patch("services.price_snapshot_service.get_db_context", return_value=mock_repo_cm),
            patch(
                "services.price_snapshot_service.PriceSnapshotRepository",
                return_value=mock_repo,
            ),
        ):
            result = await service.capture_all_property_prices()

        assert result["captured"] == 1
        assert result["properties_checked"] == 1
        mock_repo.create.assert_called_once_with(
            property_id="prop-001",
            price=500000.0,
            price_per_sqm=10000.0,
            currency="PLN",
            source="scheduled",
        )

    @pytest.mark.asyncio
    async def test_skips_unchanged_price(self):
        """Skips snapshot when price hasn't changed since last capture."""
        service = PriceSnapshotService()

        prop = MagicMock()
        prop.id = "prop-002"
        prop.price = 300000
        prop.area_sqm = 40
        prop.currency = "PLN"

        mock_collection = MagicMock()
        mock_collection.properties = [prop]

        latest_snapshot = MagicMock()
        latest_snapshot.price = 300000

        mock_repo = AsyncMock()
        mock_repo.get_latest_for_property.return_value = latest_snapshot

        mock_session = AsyncMock()
        mock_repo_cm = AsyncMock()
        mock_repo_cm.__aenter__ = AsyncMock(return_value=mock_session)
        mock_repo_cm.__aexit__ = AsyncMock(return_value=False)

        with (
            patch("services.price_snapshot_service.load_collection", return_value=mock_collection),
            patch("services.price_snapshot_service.get_db_context", return_value=mock_repo_cm),
            patch(
                "services.price_snapshot_service.PriceSnapshotRepository",
                return_value=mock_repo,
            ),
        ):
            result = await service.capture_all_property_prices()

        assert result["skipped"] == 1
        assert result["captured"] == 0
        mock_repo.create.assert_not_called()

    @pytest.mark.asyncio
    async def test_skips_property_without_id_or_price(self):
        """Skips properties that have no id or price."""
        service = PriceSnapshotService()

        prop_no_id = MagicMock(spec=[])
        prop_no_price = MagicMock(spec=[])
        # Explicitly set attributes
        prop_no_id.price = 100000
        type(prop_no_id).id = property(lambda self: None)
        prop_no_price.id = "prop-003"
        type(prop_no_price).price = property(lambda self: None)

        mock_collection = MagicMock()
        mock_collection.properties = [prop_no_id, prop_no_price]

        mock_session = AsyncMock()
        mock_repo_cm = AsyncMock()
        mock_repo_cm.__aenter__ = AsyncMock(return_value=mock_session)
        mock_repo_cm.__aexit__ = AsyncMock(return_value=False)

        with (
            patch("services.price_snapshot_service.load_collection", return_value=mock_collection),
            patch("services.price_snapshot_service.get_db_context", return_value=mock_repo_cm),
        ):
            result = await service.capture_all_property_prices()

        assert result["captured"] == 0
        assert result["properties_checked"] == 0

    @pytest.mark.asyncio
    async def test_records_source_parameter(self):
        """Passes source parameter through to repository."""
        service = PriceSnapshotService()

        prop = MagicMock()
        prop.id = "prop-010"
        prop.price = 200000
        prop.area_sqm = 30
        prop.currency = "PLN"

        mock_collection = MagicMock()
        mock_collection.properties = [prop]

        mock_repo = AsyncMock()
        mock_repo.get_latest_for_property.return_value = None

        mock_session = AsyncMock()
        mock_repo_cm = AsyncMock()
        mock_repo_cm.__aenter__ = AsyncMock(return_value=mock_session)
        mock_repo_cm.__aexit__ = AsyncMock(return_value=False)

        with (
            patch("services.price_snapshot_service.load_collection", return_value=mock_collection),
            patch("services.price_snapshot_service.get_db_context", return_value=mock_repo_cm),
            patch(
                "services.price_snapshot_service.PriceSnapshotRepository",
                return_value=mock_repo,
            ),
        ):
            await service.capture_all_property_prices(source="manual")

        mock_repo.create.assert_called_once()
        call_kwargs = mock_repo.create.call_args[1]
        assert call_kwargs["source"] == "manual"

    @pytest.mark.asyncio
    async def test_handles_error_per_property_gracefully(self):
        """Continues processing when a single property raises an error."""
        service = PriceSnapshotService()

        bad_prop = MagicMock()
        bad_prop.id = "bad-prop"
        bad_prop.price = 300000
        bad_prop.area_sqm = 50
        bad_prop.currency = "PLN"

        good_prop = MagicMock()
        good_prop.id = "good-prop"
        good_prop.price = 400000
        good_prop.area_sqm = 50
        good_prop.currency = "PLN"

        mock_collection = MagicMock()
        mock_collection.properties = [bad_prop, good_prop]

        mock_repo = AsyncMock()
        # First call for bad_prop raises, second for good_prop succeeds
        mock_repo.get_latest_for_property.side_effect = [
            Exception("DB error"),
            None,
        ]
        mock_repo.create = AsyncMock()

        mock_session = AsyncMock()
        mock_repo_cm = AsyncMock()
        mock_repo_cm.__aenter__ = AsyncMock(return_value=mock_session)
        mock_repo_cm.__aexit__ = AsyncMock(return_value=False)

        with (
            patch("services.price_snapshot_service.load_collection", return_value=mock_collection),
            patch("services.price_snapshot_service.get_db_context", return_value=mock_repo_cm),
            patch(
                "services.price_snapshot_service.PriceSnapshotRepository",
                return_value=mock_repo,
            ),
        ):
            result = await service.capture_all_property_prices()

        assert result["captured"] == 1
        assert len(result["errors"]) == 1


class TestGetPriceHistory:
    """Tests for get_price_history method."""

    @pytest.mark.asyncio
    async def test_returns_formatted_snapshots(self):
        """Returns list of dicts with ISO-formatted dates."""
        service = PriceSnapshotService()

        snap = MagicMock()
        snap.id = 1
        snap.property_id = "prop-001"
        snap.price = 500000
        snap.price_per_sqm = 10000.0
        snap.currency = "PLN"
        snap.source = "scheduled"
        snap.recorded_at = datetime(2025, 1, 15, 12, 0, 0, tzinfo=timezone.utc)

        mock_repo = AsyncMock()
        mock_repo.get_by_property.return_value = [snap]

        mock_session = AsyncMock()
        mock_repo_cm = AsyncMock()
        mock_repo_cm.__aenter__ = AsyncMock(return_value=mock_session)
        mock_repo_cm.__aexit__ = AsyncMock(return_value=False)

        with (
            patch("services.price_snapshot_service.get_db_context", return_value=mock_repo_cm),
            patch(
                "services.price_snapshot_service.PriceSnapshotRepository",
                return_value=mock_repo,
            ),
        ):
            result = await service.get_price_history("prop-001")

        assert len(result) == 1
        assert result[0]["id"] == 1
        assert result[0]["price"] == 500000
        assert result[0]["recorded_at"] == "2025-01-15T12:00:00+00:00"

    @pytest.mark.asyncio
    async def test_passes_limit_to_repository(self):
        """Forwards limit parameter to repository."""
        service = PriceSnapshotService()

        mock_repo = AsyncMock()
        mock_repo.get_by_property.return_value = []

        mock_session = AsyncMock()
        mock_repo_cm = AsyncMock()
        mock_repo_cm.__aenter__ = AsyncMock(return_value=mock_session)
        mock_repo_cm.__aexit__ = AsyncMock(return_value=False)

        with (
            patch("services.price_snapshot_service.get_db_context", return_value=mock_repo_cm),
            patch(
                "services.price_snapshot_service.PriceSnapshotRepository",
                return_value=mock_repo,
            ),
        ):
            await service.get_price_history("prop-001", limit=10)

        mock_repo.get_by_property.assert_called_once_with("prop-001", limit=10)

    @pytest.mark.asyncio
    async def test_handles_none_recorded_at(self):
        """Returns None for recorded_at when snapshot has no date."""
        service = PriceSnapshotService()

        snap = MagicMock()
        snap.id = 2
        snap.property_id = "prop-002"
        snap.price = 300000
        snap.price_per_sqm = 7500.0
        snap.currency = "PLN"
        snap.source = "manual"
        snap.recorded_at = None

        mock_repo = AsyncMock()
        mock_repo.get_by_property.return_value = [snap]

        mock_session = AsyncMock()
        mock_repo_cm = AsyncMock()
        mock_repo_cm.__aenter__ = AsyncMock(return_value=mock_session)
        mock_repo_cm.__aexit__ = AsyncMock(return_value=False)

        with (
            patch("services.price_snapshot_service.get_db_context", return_value=mock_repo_cm),
            patch(
                "services.price_snapshot_service.PriceSnapshotRepository",
                return_value=mock_repo,
            ),
        ):
            result = await service.get_price_history("prop-002")

        assert result[0]["recorded_at"] is None


class TestCleanupOldSnapshots:
    """Tests for cleanup_old_snapshots method."""

    @pytest.mark.asyncio
    async def test_delegates_to_repository(self):
        """Calls repo.cleanup_old_snapshots and returns count."""
        service = PriceSnapshotService()

        mock_repo = AsyncMock()
        mock_repo.cleanup_old_snapshots.return_value = 42

        mock_session = AsyncMock()
        mock_repo_cm = AsyncMock()
        mock_repo_cm.__aenter__ = AsyncMock(return_value=mock_session)
        mock_repo_cm.__aexit__ = AsyncMock(return_value=False)

        with (
            patch("services.price_snapshot_service.get_db_context", return_value=mock_repo_cm),
            patch(
                "services.price_snapshot_service.PriceSnapshotRepository",
                return_value=mock_repo,
            ),
        ):
            result = await service.cleanup_old_snapshots(days_to_keep=90)

        assert result == 42
        mock_repo.cleanup_old_snapshots.assert_called_once_with(90)

    @pytest.mark.asyncio
    async def test_uses_default_days(self):
        """Defaults to 365 days when no argument given."""
        service = PriceSnapshotService()

        mock_repo = AsyncMock()
        mock_repo.cleanup_old_snapshots.return_value = 0

        mock_session = AsyncMock()
        mock_repo_cm = AsyncMock()
        mock_repo_cm.__aenter__ = AsyncMock(return_value=mock_session)
        mock_repo_cm.__aexit__ = AsyncMock(return_value=False)

        with (
            patch("services.price_snapshot_service.get_db_context", return_value=mock_repo_cm),
            patch(
                "services.price_snapshot_service.PriceSnapshotRepository",
                return_value=mock_repo,
            ),
        ):
            await service.cleanup_old_snapshots()

        mock_repo.cleanup_old_snapshots.assert_called_once_with(365)
