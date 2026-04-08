"""
Sentry SDK initialization for error tracking and APM.

Initializes Sentry with FastAPI integration, PII filtering,
and performance monitoring for search/chat/RAG transactions.
"""

import logging

import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.logging import LoggingIntegration

from config.settings import get_settings

logger = logging.getLogger(__name__)

# PII fields to redact from Sentry events
_PII_FIELDS = frozenset(
    {
        "email",
        "password",
        "token",
        "authorization",
        "cookie",
        "x-api-key",
        "x-session-token",
        "query",
        "message",
        "question",
    }
)


def _before_send(event: dict, hint: dict) -> dict | None:
    """Filter PII from Sentry events before sending."""
    # Redact PII from request headers
    request = event.get("request", {})
    headers = request.get("headers")
    if headers and isinstance(headers, dict):
        for key in list(headers.keys()):
            if key.lower().replace("-", "").replace("_", "") in {
                f.replace("-", "").replace("_", "") for f in _PII_FIELDS
            }:
                headers[key] = "[Redacted]"

    # Redact PII from request body
    data = request.get("data")
    if data and isinstance(data, dict):
        for key in list(data.keys()):
            if key.lower() in _PII_FIELDS:
                data[key] = "[Redacted]"

    # Redact from extra context
    extra = event.get("extra", {})
    if isinstance(extra, dict):
        for key in list(extra.keys()):
            if key.lower() in _PII_FIELDS:
                extra[key] = "[Redacted]"

    return event


def init_sentry() -> bool:
    """
    Initialize Sentry SDK if DSN is configured.

    Returns:
        True if Sentry was initialized, False otherwise.
    """
    settings = get_settings()
    dsn = settings.sentry_dsn

    if not dsn:
        logger.info("Sentry DSN not configured — error tracking disabled")
        return False

    sentry_sdk.init(
        dsn=dsn,
        environment=settings.sentry_environment,
        release=f"ai-real-estate-assistant@{settings.version}",
        traces_sample_rate=settings.sentry_traces_sample_rate,
        integrations=[
            FastApiIntegration(),
            LoggingIntegration(
                level=logging.INFO,
                event_level=logging.ERROR,
            ),
        ],
        before_send=_before_send,
        send_default_pii=False,
        attach_stacktrace=True,
        max_breadcrumbs=50,
    )

    logger.info(
        "Sentry initialized: env=%s, traces_rate=%.1f%%",
        settings.sentry_environment,
        settings.sentry_traces_sample_rate * 100,
    )
    return True


def add_llm_breadcrumb(provider: str, model: str, **kwargs) -> None:
    """Add a breadcrumb for LLM provider calls."""
    sentry_sdk.add_breadcrumb(
        category="llm",
        message=f"LLM call: {provider}/{model}",
        level="info",
        data={"provider": provider, "model": model, **kwargs},
    )


def set_user_context(user_id: str | None = None, email: str | None = None) -> None:
    """Set user context for Sentry events (email is hashed for privacy)."""
    if user_id:
        sentry_sdk.set_user(
            {
                "id": user_id,
                # Don't send raw email to Sentry
                "email_hash": hash(email) if email else None,
            }
        )
    else:
        sentry_sdk.set_user(None)
