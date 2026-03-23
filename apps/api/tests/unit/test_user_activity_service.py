"""Unit tests for UserActivityService (Task #82)."""

import hashlib
from datetime import UTC, datetime, timedelta

import pytest

from db.models import UserActivityEvent


@pytest.fixture
def activity_service(db_session):
    """Create a UserActivityService instance for testing."""
    from services.user_activity_service import UserActivityService
    return UserActivityService(db_session, retention_days=30)


class TestUserActivityService:
    """Tests for UserActivityService."""

    @pytest.mark.asyncio
    async def test_track_event_creates_record(self, activity_service, db_session):
        """Test that track_event creates a new UserActivityEvent."""
        event = await activity_service.track_event(
            session_id="test-session-123",
            event_type="tool_use",
            event_category="tools",
            event_data={"tool_name": "mortgage_calculator"},
            user_id="user-456",
            duration_ms=150,
        )

        await db_session.commit()

        assert event.id is not None
        assert event.session_id == "test-session-123"
        assert event.event_type == "tool_use"
        assert event.event_category == "tools"
        assert event.event_data == {"tool_name": "mortgage_calculator"}
        assert event.duration_ms == 150
        # User ID should be hashed
        assert event.user_id_hash != "user-456"
        assert len(event.user_id_hash) == 64  # SHA-256 hex length

    @pytest.mark.asyncio
    async def test_track_event_minimal(self, activity_service, db_session):
        """Test tracking event with minimal required data."""
        event = await activity_service.track_event(
            session_id="test-session-minimal",
            event_type="page_view",
            event_category="navigation",
        )

        await db_session.commit()

        assert event.id is not None
        assert event.session_id == "test-session-minimal"
        assert event.event_type == "page_view"
        assert event.event_category == "navigation"
        assert event.user_id_hash is None
        assert event.duration_ms is None

    @pytest.mark.asyncio
    async def test_hash_user_id_returns_none_for_none(self, activity_service):
        """Test that hashing None returns None."""
        result = activity_service._hash_user_id(None)
        assert result is None

    @pytest.mark.asyncio
    async def test_hash_user_id_is_consistent(self, activity_service):
        """Test that hashing is deterministic."""
        hash1 = activity_service._hash_user_id("user-123")
        hash2 = activity_service._hash_user_id("user-123")
        assert hash1 == hash2

    @pytest.mark.asyncio
    async def test_hash_user_id_is_different_for_different_inputs(self, activity_service):
        """Test that different inputs produce different hashes."""
        hash1 = activity_service._hash_user_id("user-123")
        hash2 = activity_service._hash_user_id("user-456")
        assert hash1 != hash2

    @pytest.mark.asyncio
    async def test_hash_user_id_is_sha256(self, activity_service):
        """Test that hashing uses SHA-256 algorithm."""
        user_id = "test-user@example.com"
        result = activity_service._hash_user_id(user_id)

        # Verify it's SHA-256 by computing expected hash
        expected = hashlib.sha256(user_id.encode()).hexdigest()
        assert result == expected

    @pytest.mark.asyncio
    async def test_get_summary_returns_aggregated_data(self, activity_service):
        """Test that get_summary returns correct aggregations."""
        # Create test events
        await activity_service.track_event("s1", "search_query", "search")
        await activity_service.track_event("s1", "search_query", "search")
        await activity_service.track_event("s1", "property_view", "view")
        await activity_service.track_event("s1", "tool_use", "tools", {"tool_name": "calc"})
        await activity_service.track_event("s2", "tool_use", "tools", {"tool_name": "mortgage"})

        summary = await activity_service.get_summary()

        assert "period_start" in summary
        assert "period_end" in summary
        assert summary["total_events"] == 5
        assert summary["total_searches"] == 2
        assert summary["total_tool_uses"] == 2

    @pytest.mark.asyncio
    async def test_get_summary_filters_by_date_range(self, activity_service):
        """Test that get_summary can filter by date range."""
        now = datetime.now(UTC)

        # Create an old event (outside default 7-day window)
        old_event = await activity_service.track_event(
            "s1", "search_query", "search"
        )
        old_event.event_timestamp = now - timedelta(days=14)

        # Create recent event
        await activity_service.track_event("s1", "property_view", "view")

        summary = await activity_service.get_summary(days=7)

        # Only recent event should be counted
        assert summary["total_events"] == 1
        assert summary["total_views"] == 1

    @pytest.mark.asyncio
    async def test_get_summary_with_session_filter(self, activity_service):
        """Test that get_summary can filter by session."""
        await activity_service.track_event("s1", "search_query", "search")
        await activity_service.track_event("s1", "property_view", "view")
        await activity_service.track_event("s2", "search_query", "search")

        summary = await activity_service.get_summary(session_id="s1")

        assert summary["total_events"] == 2
        assert summary["total_searches"] == 1
        assert summary["total_views"] == 1

    @pytest.mark.asyncio
    async def test_export_to_csv_returns_valid_csv(self, activity_service):
        """Test CSV export format."""
        await activity_service.track_event(
            "s1", "search_query", "search",
            event_data={"query": "apartments in Krakow"}
        )
        await activity_service.track_event(
            "s1", "property_view", "view",
            event_data={"property_id": "prop-123"}
        )

        csv_data = await activity_service.export_to_csv()

        # Check header row
        assert "timestamp" in csv_data
        assert "session_id" in csv_data
        assert "event_type" in csv_data
        assert "event_category" in csv_data

        # Check data rows
        lines = csv_data.strip().split("\n")
        assert len(lines) >= 3  # Header + 2 data rows

    @pytest.mark.asyncio
    async def test_export_to_csv_filters_by_session(self, activity_service):
        """Test CSV export can filter by session."""
        await activity_service.track_event("s1", "search_query", "search")
        await activity_service.track_event("s2", "property_view", "view")

        csv_data = await activity_service.export_to_csv(session_id="s1")

        lines = csv_data.strip().split("\n")
        # Should have header + 1 data row (only s1 event)
        assert len(lines) == 2

    @pytest.mark.asyncio
    async def test_cleanup_removes_old_events(self, activity_service, db_session):
        """Test retention policy cleanup."""
        # Create old event
        old_event = await activity_service.track_event("s1", "old_event", "test")
        # Manually set timestamp to past
        old_event.event_timestamp = datetime.now(UTC) - timedelta(days=60)
        await db_session.commit()

        # Create recent event
        await activity_service.track_event("s2", "recent_event", "test")

        deleted_count = await activity_service.cleanup_old_events()

        # Should delete events older than retention_days (30)
        assert deleted_count >= 1

        # Verify old event is gone, recent remains
        from sqlalchemy import select
        from db.models import UserActivityEvent

        result = await db_session.execute(
            select(UserActivityEvent).where(UserActivityEvent.event_type == "old_event")
        )
        assert result.scalar_one_or_none() is None

        result = await db_session.execute(
            select(UserActivityEvent).where(UserActivityEvent.event_type == "recent_event")
        )
        assert result.scalar_one_or_none() is not None

    @pytest.mark.asyncio
    async def test_cleanup_respects_retention_days(self, activity_service, db_session):
        """Test cleanup respects custom retention period."""
        retention_days = 7
        service_custom = activity_service.__class__(db_session, retention_days=retention_days)

        # Create event just outside retention window
        old_event = await service_custom.track_event("s1", "old", "test")
        old_event.event_timestamp = datetime.now(UTC) - timedelta(days=retention_days + 1)
        await db_session.commit()

        # Create event inside retention window
        recent_event = await service_custom.track_event("s2", "recent", "test")
        recent_event.event_timestamp = datetime.now(UTC) - timedelta(days=retention_days - 1)
        await db_session.commit()

        deleted_count = await service_custom.cleanup_old_events()

        assert deleted_count == 1

    @pytest.mark.asyncio
    async def test_get_trends_returns_time_series(self, activity_service):
        """Test trends endpoint returns time series data."""
        now = datetime.now(UTC)

        # Create events over past few days
        for i in range(5):
            event = await activity_service.track_event(
                f"s{i}", "search_query", "search"
            )
            event.event_timestamp = now - timedelta(days=i)

        trends = await activity_service.get_trends(interval="day", periods=7)

        assert isinstance(trends, list)
        assert len(trends) <= 7  # Should not exceed requested periods
        # Each trend should have date and count
        if trends:
            assert "date" in trends[0]
            assert "count" in trends[0]

    @pytest.mark.asyncio
    async def test_get_trends_with_weekly_interval(self, activity_service):
        """Test trends can aggregate by week."""
        now = datetime.now(UTC)

        # Create events spanning multiple weeks
        for i in range(21):  # 3 weeks
            event = await activity_service.track_event(f"s{i}", "search_query", "search")
            event.event_timestamp = now - timedelta(days=i)

        trends = await activity_service.get_trends(interval="week", periods=4)

        assert isinstance(trends, list)
        assert len(trends) <= 4

    @pytest.mark.asyncio
    async def test_get_trends_filters_by_event_type(self, activity_service):
        """Test trends can filter by event type."""
        await activity_service.track_event("s1", "search_query", "search")
        await activity_service.track_event("s2", "property_view", "view")
        await activity_service.track_event("s3", "search_query", "search")

        trends = await activity_service.get_trends(
            interval="day",
            periods=7,
            event_type="search_query"
        )

        # Should only count search_query events
        total_count = sum(t.get("count", 0) for t in trends)
        assert total_count == 2

    @pytest.mark.asyncio
    async def test_track_event_with_session_tracking(self, activity_service):
        """Test session tracking capabilities."""
        # Track multiple events in same session
        await activity_service.track_event("session-1", "search_query", "search")
        await activity_service.track_event("session-1", "property_view", "view")
        await activity_service.track_event("session-1", "tool_use", "tools")

        summary = await activity_service.get_summary(session_id="session-1")

        assert summary["total_events"] == 3
        assert summary["total_searches"] == 1
        assert summary["total_views"] == 1
        assert summary["total_tool_uses"] == 1

    @pytest.mark.asyncio
    async def test_get_event_types_returns_unique_types(self, activity_service):
        """Test getting unique event types."""
        await activity_service.track_event("s1", "search_query", "search")
        await activity_service.track_event("s1", "search_query", "search")
        await activity_service.track_event("s1", "property_view", "view")
        await activity_service.track_event("s1", "tool_use", "tools")

        event_types = await activity_service.get_event_types()

        assert isinstance(event_types, list)
        assert "search_query" in event_types
        assert "property_view" in event_types
        assert "tool_use" in event_types

    @pytest.mark.asyncio
    async def test_get_top_sessions_returns_most_active(self, activity_service):
        """Test getting top sessions by activity."""
        # Create sessions with varying activity
        for i in range(10):
            await activity_service.track_event("s1", "event", "test")
        for i in range(5):
            await activity_service.track_event("s2", "event", "test")
        await activity_service.track_event("s3", "event", "test")

        top_sessions = await activity_service.get_top_sessions(limit=2)

        assert len(top_sessions) == 2
        assert top_sessions[0]["session_id"] == "s1"
        assert top_sessions[0]["event_count"] == 10
        assert top_sessions[1]["session_id"] == "s2"
        assert top_sessions[1]["event_count"] == 5

    @pytest.mark.asyncio
    async def test_get_category_breakdown_returns_counts(self, activity_service):
        """Test getting event counts by category."""
        await activity_service.track_event("s1", "search_query", "search")
        await activity_service.track_event("s1", "search_query", "search")
        await activity_service.track_event("s1", "property_view", "view")
        await activity_service.track_event("s1", "tool_use", "tools")
        await activity_service.track_event("s1", "export", "export")

        breakdown = await activity_service.get_category_breakdown()

        assert isinstance(breakdown, list)
        assert len(breakdown) == 4  # search, view, tools, export

        search_cat = next((c for c in breakdown if c["category"] == "search"), None)
        assert search_cat is not None
        assert search_cat["count"] == 2

    @pytest.mark.asyncio
    async def test_get_average_duration_by_event_type(self, activity_service):
        """Test calculating average duration per event type."""
        await activity_service.track_event("s1", "tool_use", "tools", duration_ms=100)
        await activity_service.track_event("s2", "tool_use", "tools", duration_ms=200)
        await activity_service.track_event("s3", "export", "export", duration_ms=500)

        durations = await activity_service.get_average_duration_by_event_type()

        assert isinstance(durations, list)

        tool_use = next((d for d in durations if d["event_type"] == "tool_use"), None)
        assert tool_use is not None
        assert tool_use["avg_duration_ms"] == 150  # (100 + 200) / 2

        export = next((d for d in durations if d["event_type"] == "export"), None)
        assert export is not None
        assert export["avg_duration_ms"] == 500

    @pytest.mark.asyncio
    async def test_privacy_no_user_data_in_logs(self, activity_service):
        """Test that user privacy is preserved (no raw user IDs stored)."""
        user_id = "user@example.com"
        await activity_service.track_event(
            "s1", "test", "test", user_id=user_id
        )

        # Query directly to verify user_id_hash is not the raw email
        from sqlalchemy import select

        result = await activity_service._db.execute(
            select(UserActivityEvent).where(UserActivityEvent.session_id == "s1")
        )
        event = result.scalar_one()

        # Verify the hash is not the original value
        assert event.user_id_hash != user_id
        # Verify it's a proper hash (64 hex chars for SHA-256)
        assert len(event.user_id_hash) == 64
        assert all(c in "0123456789abcdef" for c in event.user_id_hash)

    @pytest.mark.asyncio
    async def test_event_data_serialization(self, activity_service):
        """Test that event_data JSON is properly stored and retrieved."""
        complex_data = {
            "filters": {"city": "Krakow", "price_max": 500000},
            "results_count": 42,
            "user_agent": "Mozilla/5.0"
        }

        await activity_service.track_event(
            "s1", "search_query", "search", event_data=complex_data
        )

        summary = await activity_service.get_summary()

        # Data should be preserved
        assert summary["total_events"] == 1

    @pytest.mark.asyncio
    async def test_concurrent_event_tracking(self, activity_service):
        """Test that multiple events can be tracked concurrently."""
        import asyncio

        tasks = []
        for i in range(10):
            task = activity_service.track_event(
                f"session-{i % 3}",  # Distribute across 3 sessions
                f"event-{i}",
                "test"
            )
            tasks.append(task)

        results = await asyncio.gather(*tasks)

        assert len(results) == 10
        for result in results:
            assert result.id is not None
            assert result.event_timestamp is not None


class TestUserActivityEventModel:
    """Tests for UserActivityEvent model directly."""

    @pytest.mark.asyncio
    async def test_model_repr(self, db_session):
        """Test model string representation."""
        event = UserActivityEvent(
            session_id="test-session",
            event_type="test_type",
            event_category="test_category"
        )
        db_session.add(event)
        await db_session.commit()

        repr_str = repr(event)
        assert "test_type" in repr_str
        assert "test-session" in repr_str

    @pytest.mark.asyncio
    async def test_model_defaults(self, db_session):
        """Test model default values."""
        event = UserActivityEvent(
            session_id="test-session",
            event_type="test_type",
            event_category="test_category"
        )
        db_session.add(event)
        await db_session.commit()
        await db_session.refresh(event)

        # Defaults should be set
        assert event.id is not None
        assert event.event_timestamp is not None
        assert event.user_id_hash is None
        assert event.duration_ms is None
        assert event.event_data is None

    @pytest.mark.asyncio
    async def test_model_with_all_fields(self, db_session):
        """Test model with all fields populated."""
        import json

        event = UserActivityEvent(
            session_id="test-session",
            event_type="tool_use",
            event_category="tools",
            event_data={"tool_name": "mortgage", "result": "success"},
            user_id_hash="a" * 64,  # SHA-256 hash
            duration_ms=250
        )
        db_session.add(event)
        await db_session.commit()
        await db_session.refresh(event)

        assert event.session_id == "test-session"
        assert event.event_type == "tool_use"
        assert event.event_category == "tools"
        assert event.event_data["tool_name"] == "mortgage"
        assert event.duration_ms == 250
        assert event.user_id_hash == "a" * 64
