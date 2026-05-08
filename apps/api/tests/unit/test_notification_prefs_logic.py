"""Tests for notification_preferences data classes and logic."""

from datetime import datetime

from notifications.alert_manager import AlertType
from notifications.notification_preferences import (
    AlertFrequency,
    DigestDay,
    NotificationPreferences,
)


class TestAlertFrequency:
    def test_values(self):
        assert AlertFrequency.INSTANT == "instant"
        assert AlertFrequency.HOURLY == "hourly"
        assert AlertFrequency.DAILY == "daily"
        assert AlertFrequency.WEEKLY == "weekly"


class TestDigestDay:
    def test_all_days(self):
        assert len(DigestDay) == 7
        assert DigestDay.MONDAY == "monday"
        assert DigestDay.SUNDAY == "sunday"


class TestNotificationPreferences:
    def test_defaults(self):
        prefs = NotificationPreferences(user_email="test@test.com")
        assert prefs.alert_frequency == AlertFrequency.INSTANT
        assert prefs.price_drop_threshold == 5.0
        assert prefs.max_alerts_per_day == 10
        assert prefs.enabled is True
        assert prefs.expert_mode is False
        assert prefs.marketing_emails is False

    def test_to_dict(self):
        prefs = NotificationPreferences(user_email="test@test.com")
        d = prefs.to_dict()
        assert d["user_email"] == "test@test.com"
        assert isinstance(d["enabled_alerts"], list)
        assert d["alert_frequency"] == "instant"
        assert d["weekly_digest_day"] == "monday"
        assert "created_at" in d

    def test_from_dict(self):
        prefs = NotificationPreferences(user_email="test@test.com")
        d = prefs.to_dict()
        restored = NotificationPreferences.from_dict(d)
        assert restored.user_email == "test@test.com"
        assert restored.alert_frequency == AlertFrequency.INSTANT

    def test_is_alert_enabled(self):
        prefs = NotificationPreferences(user_email="test@test.com")
        assert prefs.is_alert_enabled(AlertType.PRICE_DROP) is True
        assert prefs.is_alert_enabled(AlertType.NEW_PROPERTY) is True

    def test_is_alert_disabled_when_notifications_off(self):
        prefs = NotificationPreferences(user_email="test@test.com", enabled=False)
        assert prefs.is_alert_enabled(AlertType.PRICE_DROP) is False

    def test_is_in_quiet_hours_no_times(self):
        prefs = NotificationPreferences(
            user_email="test@test.com", quiet_hours_start=None, quiet_hours_end=None
        )
        assert prefs.is_in_quiet_hours() is False

    def test_is_in_quiet_hours_during(self):
        prefs = NotificationPreferences(
            user_email="test@test.com",
            quiet_hours_start="22:00",
            quiet_hours_end="08:00",
        )
        check = datetime(2025, 1, 1, 23, 0)
        assert prefs.is_in_quiet_hours(check) is True

    def test_is_not_in_quiet_hours(self):
        prefs = NotificationPreferences(
            user_email="test@test.com",
            quiet_hours_start="22:00",
            quiet_hours_end="08:00",
        )
        check = datetime(2025, 1, 1, 14, 0)
        assert prefs.is_in_quiet_hours(check) is False

    def test_is_in_quiet_hours_same_day_range(self):
        prefs = NotificationPreferences(
            user_email="test@test.com",
            quiet_hours_start="12:00",
            quiet_hours_end="14:00",
        )
        check = datetime(2025, 1, 1, 13, 0)
        assert prefs.is_in_quiet_hours(check) is True

    def test_should_send_alert_basic(self):
        prefs = NotificationPreferences(user_email="test@test.com")
        assert prefs.should_send_alert(AlertType.PRICE_DROP) is True

    def test_should_not_send_when_disabled(self):
        prefs = NotificationPreferences(user_email="test@test.com", enabled=False)
        assert prefs.should_send_alert(AlertType.PRICE_DROP) is False

    def test_should_not_send_when_alert_type_disabled(self):
        prefs = NotificationPreferences(user_email="test@test.com", enabled_alerts=set())
        assert prefs.should_send_alert(AlertType.PRICE_DROP) is False

    def test_should_not_send_over_daily_limit(self):
        prefs = NotificationPreferences(user_email="test@test.com", max_alerts_per_day=5)
        assert prefs.should_send_alert(AlertType.PRICE_DROP, alerts_sent_today=5) is False

    def test_digest_requires_daily_or_weekly(self):
        prefs = NotificationPreferences(
            user_email="test@test.com", alert_frequency=AlertFrequency.INSTANT
        )
        assert prefs.should_send_alert(AlertType.DIGEST) is False

    def test_digest_daily_enabled(self):
        prefs = NotificationPreferences(
            user_email="test@test.com", alert_frequency=AlertFrequency.DAILY
        )
        # Provide check_time outside quiet hours (22:00-08:00) so the test
        # does not fail when run during quiet hours.
        check = datetime(2025, 1, 1, 14, 0)
        assert prefs.should_send_alert(AlertType.DIGEST, check_time=check) is True

    def test_digest_weekly_correct_day(self):
        prefs = NotificationPreferences(
            user_email="test@test.com",
            alert_frequency=AlertFrequency.WEEKLY,
            weekly_digest_day=DigestDay.MONDAY,
        )
        check = datetime(2025, 1, 6, 9, 0)
        assert prefs.should_send_alert(AlertType.DIGEST, check_time=check) is True

    def test_digest_weekly_wrong_day(self):
        prefs = NotificationPreferences(
            user_email="test@test.com",
            alert_frequency=AlertFrequency.WEEKLY,
            weekly_digest_day=DigestDay.FRIDAY,
        )
        check = datetime(2025, 1, 6, 9, 0)
        assert prefs.should_send_alert(AlertType.DIGEST, check_time=check) is False

    def test_get_search_preferences_default(self):
        prefs = NotificationPreferences(user_email="test@test.com")
        result = prefs.get_search_preferences("search-1")
        assert isinstance(result, dict)

    def test_get_search_preferences_custom(self):
        prefs = NotificationPreferences(
            user_email="test@test.com",
            per_search_settings={"search-1": {"threshold": 10.0}},
        )
        result = prefs.get_search_preferences("search-1")
        assert result["threshold"] == 10.0

    def test_custom_enabled_alerts(self):
        prefs = NotificationPreferences(
            user_email="test@test.com", enabled_alerts={AlertType.PRICE_DROP}
        )
        assert prefs.is_alert_enabled(AlertType.PRICE_DROP) is True
        assert prefs.is_alert_enabled(AlertType.NEW_PROPERTY) is False
