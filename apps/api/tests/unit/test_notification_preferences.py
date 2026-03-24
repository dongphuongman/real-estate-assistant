"""Unit tests for notification preferences functionality (Task #86)."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from db.models import NotificationPreferenceDB, User
from db.repositories import NotificationPreferenceRepository


@pytest.fixture
def mock_session():
    """Create a mock async session."""
    session = AsyncMock()
    session.execute = AsyncMock()
    session.add = MagicMock()
    session.flush = AsyncMock()
    session.delete = AsyncMock()
    return session


@pytest.fixture
def sample_user():
    """Create a sample user."""
    user = User(
        id=str(uuid4()),
        email="test@example.com",
        hashed_password="hashed",
        full_name="Test User",
        role="user",
        is_verified=True,
        is_active=True,
    )
    return user


@pytest.fixture
def sample_prefs(sample_user):
    """Create sample notification preferences."""
    return NotificationPreferenceDB(
        id=str(uuid4()),
        user_id=sample_user.id,
        price_alerts_enabled=True,
        new_listings_enabled=True,
        saved_search_enabled=True,
        market_updates_enabled=False,
        alert_frequency="daily",
        email_enabled=True,
        push_enabled=False,
        in_app_enabled=True,
        quiet_hours_start=None,
        quiet_hours_end=None,
        price_drop_threshold=5.0,
        daily_digest_time="09:00",
        weekly_digest_day="monday",
        expert_mode=False,
        marketing_emails=False,
        unsubscribe_token=str(uuid4()).replace("-", "") + str(uuid4()).replace("-", ""),
    )


class TestNotificationPreferenceRepository:
    """Tests for NotificationPreferenceRepository."""

    @pytest.mark.asyncio
    async def test_get_by_user_id_found(self, mock_session, sample_prefs):
        """Test getting preferences by user ID when found."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_prefs
        mock_session.execute.return_value = mock_result

        repo = NotificationPreferenceRepository(mock_session)
        result = await repo.get_by_user_id(sample_prefs.user_id)

        assert result == sample_prefs
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_by_user_id_not_found(self, mock_session):
        """Test getting preferences by user ID when not found."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        repo = NotificationPreferenceRepository(mock_session)
        result = await repo.get_by_user_id("nonexistent-user-id")

        assert result is None

    @pytest.mark.asyncio
    async def test_get_by_unsubscribe_token_found(self, mock_session, sample_prefs):
        """Test getting preferences by unsubscribe token when found."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_prefs
        mock_session.execute.return_value = mock_result

        repo = NotificationPreferenceRepository(mock_session)
        result = await repo.get_by_unsubscribe_token(sample_prefs.unsubscribe_token)

        assert result == sample_prefs

    @pytest.mark.asyncio
    async def test_get_by_unsubscribe_token_not_found(self, mock_session):
        """Test getting preferences by unsubscribe token when not found."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        repo = NotificationPreferenceRepository(mock_session)
        result = await repo.get_by_unsubscribe_token("invalid-token")

        assert result is None

    @pytest.mark.asyncio
    async def test_create_with_defaults(self, mock_session, sample_user):
        """Test creating preferences with default values."""
        repo = NotificationPreferenceRepository(mock_session)
        result = await repo.create(user_id=sample_user.id)

        assert result.user_id == sample_user.id
        assert result.price_alerts_enabled is True
        assert result.new_listings_enabled is True
        assert result.saved_search_enabled is True
        assert result.market_updates_enabled is False
        assert result.alert_frequency == "daily"
        assert result.email_enabled is True
        assert result.push_enabled is False
        assert result.in_app_enabled is True
        assert result.price_drop_threshold == 5.0
        assert result.daily_digest_time == "09:00"
        assert result.weekly_digest_day == "monday"
        assert result.expert_mode is False
        assert result.marketing_emails is False
        mock_session.add.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_with_custom_values(self, mock_session, sample_user):
        """Test creating preferences with custom values."""
        repo = NotificationPreferenceRepository(mock_session)
        result = await repo.create(
            user_id=sample_user.id,
            price_alerts_enabled=False,
            alert_frequency="weekly",
            push_enabled=True,
            expert_mode=True,
        )

        assert result.price_alerts_enabled is False
        assert result.alert_frequency == "weekly"
        assert result.push_enabled is True
        assert result.expert_mode is True

    @pytest.mark.asyncio
    async def test_get_or_create_existing(self, mock_session, sample_prefs):
        """Test get_or_create when preferences exist."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_prefs
        mock_session.execute.return_value = mock_result

        repo = NotificationPreferenceRepository(mock_session)
        result = await repo.get_or_create(sample_prefs.user_id)

        assert result == sample_prefs
        mock_session.add.assert_not_called()

    @pytest.mark.asyncio
    async def test_get_or_create_creates_new(self, mock_session, sample_user):
        """Test get_or_create creates new preferences when none exist."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        repo = NotificationPreferenceRepository(mock_session)
        result = await repo.get_or_create(sample_user.id)

        assert result.user_id == sample_user.id
        mock_session.add.assert_called_once()

    @pytest.mark.asyncio
    async def test_update(self, mock_session, sample_prefs):
        """Test updating preferences."""
        repo = NotificationPreferenceRepository(mock_session)
        result = await repo.update(
            sample_prefs,
            price_alerts_enabled=False,
            alert_frequency="weekly",
            quiet_hours_start="22:00",
            quiet_hours_end="08:00",
        )

        assert result.price_alerts_enabled is False
        assert result.alert_frequency == "weekly"
        assert result.quiet_hours_start == "22:00"
        assert result.quiet_hours_end == "08:00"
        mock_session.flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_unsubscribe_all(self, mock_session, sample_prefs):
        """Test unsubscribing from all notifications."""
        repo = NotificationPreferenceRepository(mock_session)
        result = await repo.unsubscribe_all(sample_prefs)

        assert result.unsubscribed_at is not None
        assert result.price_alerts_enabled is False
        assert result.new_listings_enabled is False
        assert result.saved_search_enabled is False
        assert result.market_updates_enabled is False
        assert result.marketing_emails is False
        assert result.email_enabled is False
        assert result.push_enabled is False
        mock_session.flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_unsubscribe_type_price_alerts(self, mock_session, sample_prefs):
        """Test unsubscribing from a specific notification type."""
        repo = NotificationPreferenceRepository(mock_session)
        result = await repo.unsubscribe_type(sample_prefs, "price_alerts")

        assert result.price_alerts_enabled is False
        assert "price_alerts" in result.unsubscribed_types
        # Other types should remain unchanged
        assert result.new_listings_enabled is True
        mock_session.flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_unsubscribe_type_marketing(self, mock_session, sample_prefs):
        """Test unsubscribing from marketing emails."""
        sample_prefs.marketing_emails = True
        repo = NotificationPreferenceRepository(mock_session)
        result = await repo.unsubscribe_type(sample_prefs, "marketing")

        assert result.marketing_emails is False
        assert "marketing" in result.unsubscribed_types

    @pytest.mark.asyncio
    async def test_delete(self, mock_session, sample_prefs):
        """Test deleting preferences."""
        repo = NotificationPreferenceRepository(mock_session)
        await repo.delete(sample_prefs)

        mock_session.delete.assert_called_once_with(sample_prefs)
        mock_session.flush.assert_called_once()


class TestNotificationPreferenceModel:
    """Tests for NotificationPreferenceDB model."""

    def test_is_fully_unsubscribed_false(self, sample_prefs):
        """Test is_fully_unsubscribed returns False when not unsubscribed."""
        sample_prefs.unsubscribed_at = None
        assert sample_prefs.is_fully_unsubscribed is False

    def test_is_fully_unsubscribed_true(self, sample_prefs):
        """Test is_fully_unsubscribed returns True when unsubscribed."""
        sample_prefs.unsubscribed_at = datetime.now(UTC)
        assert sample_prefs.is_fully_unsubscribed is True

    def test_repr(self, sample_prefs):
        """Test string representation."""
        repr_str = repr(sample_prefs)
        assert "NotificationPreferenceDB" in repr_str
        assert "frequency=daily" in repr_str
