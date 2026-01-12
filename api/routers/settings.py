from fastapi import APIRouter, HTTPException, Header, Query
from api.models import NotificationSettings
from notifications.notification_preferences import (
    NotificationPreferencesManager,
    AlertFrequency,
    AlertType,
)
import logging

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Settings"])

DEFAULT_USER_EMAIL = "user@example.com"
PREFS_MANAGER = NotificationPreferencesManager()


def _resolve_user_email(user_email: str | None, x_user_email: str | None) -> str:
    resolved = (user_email or x_user_email or DEFAULT_USER_EMAIL).strip()
    if not resolved:
        raise HTTPException(status_code=400, detail="Missing user email")
    return resolved


@router.get("/settings/notifications", response_model=NotificationSettings)
async def get_notification_settings(
    user_email: str | None = Query(default=None),
    x_user_email: str | None = Header(default=None, alias="X-User-Email"),
):
    """Get notification settings for the current user."""
    try:
        resolved_user_email = _resolve_user_email(user_email, x_user_email)
        prefs = PREFS_MANAGER.get_preferences(resolved_user_email)

        # Map backend preferences to frontend model
        # Logic: if DIGEST is in enabled_alerts, email_digest is True
        email_digest = prefs.is_alert_enabled(AlertType.DIGEST)

        frequency = "weekly"
        if prefs.alert_frequency == AlertFrequency.DAILY:
            frequency = "daily"
        elif prefs.alert_frequency == AlertFrequency.WEEKLY:
            frequency = "weekly"

        return NotificationSettings(
            email_digest=email_digest,
            frequency=frequency,
            expert_mode=getattr(prefs, "expert_mode", False),
            marketing_emails=getattr(prefs, "marketing_emails", False),
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching settings: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/settings/notifications", response_model=NotificationSettings)
async def update_notification_settings(
    settings: NotificationSettings,
    user_email: str | None = Query(default=None),
    x_user_email: str | None = Header(default=None, alias="X-User-Email"),
):
    """Update notification settings for the current user."""
    try:
        resolved_user_email = _resolve_user_email(user_email, x_user_email)
        prefs = PREFS_MANAGER.get_preferences(resolved_user_email)

        # Update fields
        if settings.email_digest:
            prefs.enabled_alerts.add(AlertType.DIGEST)
        else:
            prefs.enabled_alerts.discard(AlertType.DIGEST)

        # Map frequency
        if settings.frequency == "daily":
            prefs.alert_frequency = AlertFrequency.DAILY
        else:
            prefs.alert_frequency = AlertFrequency.WEEKLY

        prefs.expert_mode = settings.expert_mode
        prefs.marketing_emails = settings.marketing_emails

        PREFS_MANAGER.save_preferences(prefs)

        return settings
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating settings: {e}")
        raise HTTPException(status_code=500, detail=str(e))
