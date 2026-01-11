from fastapi import APIRouter, HTTPException
from api.models import NotificationSettings
from notifications.notification_preferences import NotificationPreferencesManager, AlertFrequency, AlertType
import logging

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Settings"])

# Use a fixed user for now since we don't have user management yet
DEFAULT_USER_EMAIL = "user@example.com"
PREFS_MANAGER = NotificationPreferencesManager()

@router.get("/settings/notifications", response_model=NotificationSettings)
async def get_notification_settings():
    """Get notification settings for the current user."""
    try:
        prefs = PREFS_MANAGER.get_preferences(DEFAULT_USER_EMAIL)
        
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
            marketing_emails=getattr(prefs, "marketing_emails", False)
        )
    except Exception as e:
        logger.error(f"Error fetching settings: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/settings/notifications", response_model=NotificationSettings)
async def update_notification_settings(settings: NotificationSettings):
    """Update notification settings for the current user."""
    try:
        prefs = PREFS_MANAGER.get_preferences(DEFAULT_USER_EMAIL)
        
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
    except Exception as e:
        logger.error(f"Error updating settings: {e}")
        raise HTTPException(status_code=500, detail=str(e))
