import logging

from fastapi import APIRouter, Header, HTTPException, Query

from api.models import ModelCatalogItem, ModelPricing, ModelProviderCatalog, NotificationSettings
from models.provider_factory import ModelProviderFactory
from notifications.notification_preferences import (
    AlertFrequency,
    AlertType,
    NotificationPreferencesManager,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Settings"])

PREFS_MANAGER = NotificationPreferencesManager()


def _resolve_user_email(user_email: str | None, x_user_email: str | None) -> str:
    resolved = (user_email or x_user_email or "").strip()
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
        raise HTTPException(status_code=500, detail=str(e)) from e


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
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/settings/models", response_model=list[ModelProviderCatalog])
async def list_model_catalog():
    """List available model providers and their models."""
    try:
        providers: list[ModelProviderCatalog] = []
        for provider_name in ModelProviderFactory.list_providers():
            provider = ModelProviderFactory.get_provider(provider_name)
            models: list[ModelCatalogItem] = []
            runtime_available: bool | None = None
            available_models: list[str] | None = None

            for model_info in provider.list_models():
                pricing = None
                if model_info.pricing:
                    pricing = ModelPricing(
                        input_price_per_1m=model_info.pricing.input_price_per_1m,
                        output_price_per_1m=model_info.pricing.output_price_per_1m,
                        currency=model_info.pricing.currency,
                    )

                models.append(
                    ModelCatalogItem(
                        id=model_info.id,
                        display_name=model_info.display_name,
                        provider_name=model_info.provider_name,
                        context_window=model_info.context_window,
                        pricing=pricing,
                        capabilities=[c.value for c in model_info.capabilities],
                        description=model_info.description,
                        recommended_for=model_info.recommended_for,
                    )
                )

            if provider.is_local and hasattr(provider, "list_available_models"):
                maybe_models = provider.list_available_models()
                if maybe_models is None:
                    runtime_available = False
                    available_models = []
                else:
                    runtime_available = True
                    available_models = list(maybe_models)

            providers.append(
                ModelProviderCatalog(
                    name=provider.name,
                    display_name=provider.display_name,
                    is_local=provider.is_local,
                    requires_api_key=provider.requires_api_key,
                    models=models,
                    runtime_available=runtime_available,
                    available_models=available_models,
                )
            )
        return providers
    except Exception as e:
        logger.error(f"Error listing model catalog: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e
