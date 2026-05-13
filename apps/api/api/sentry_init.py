"""
Sentry SDK initialization for error tracking and APM.

Initializes Sentry with FastAPI integration, PII filtering,
and performance monitoring for search/chat/RAG transactions.
"""

import logging
import subprocess

from config.settings import get_settings

logger = logging.getLogger(__name__)


def _get_git_sha() -> str:
    """Get the current git SHA for release tracking."""
    try:
        import pathlib

        repo_root = pathlib.Path(__file__).resolve().parent.parent.parent.parent
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            cwd=str(repo_root),
            text=True,
            timeout=5,
        ).strip()
    except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
        return "unknown"


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
    try:
        import sentry_sdk  # type: ignore[import-untyped]
        from sentry_sdk.integrations.fastapi import FastApiIntegration
        from sentry_sdk.integrations.logging import LoggingIntegration
    except ImportError:
        logger.warning("sentry-sdk not installed — error tracking disabled")
        return False

    settings = get_settings()
    dsn = settings.sentry_dsn

    if not dsn:
        logger.info("Sentry DSN not configured — error tracking disabled")
        return False

    git_sha = _get_git_sha()

    sentry_sdk.init(
        dsn=dsn,
        environment=settings.sentry_environment,
        release=f"ai-real-estate-assistant@{git_sha}",
        traces_sample_rate=settings.sentry_traces_sample_rate,
        integrations=[
            FastApiIntegration(),
            LoggingIntegration(
                level=logging.INFO,
                event_level=logging.ERROR,
            ),
        ],
        before_send=_before_send,  # type: ignore[arg-type]
        send_default_pii=False,
        attach_stacktrace=True,
        max_breadcrumbs=50,
    )

    # Set default tags for all events
    try:
        import sentry_sdk  # type: ignore[import-untyped]

        sentry_sdk.set_tag("component", "backend")
        sentry_sdk.set_tag("runtime", "fastapi")
    except ImportError:
        pass

    logger.info(
        "Sentry initialized: env=%s, traces_rate=%.1f%%",
        settings.sentry_environment,
        settings.sentry_traces_sample_rate * 100,
    )
    return True


def add_llm_breadcrumb(provider: str, model: str, **kwargs) -> None:
    """Add a breadcrumb for LLM provider calls."""
    try:
        import sentry_sdk  # type: ignore[import-untyped]

        sentry_sdk.add_breadcrumb(
            category="llm",
            message=f"LLM call: {provider}/{model}",
            level="info",
            data={"provider": provider, "model": model, **kwargs},
        )
    except ImportError:
        pass  # Sentry not available


def set_user_context(user_id: str | None = None, email: str | None = None) -> None:
    """Set user context for Sentry events (email is hashed for privacy)."""
    if not user_id:
        return
    try:
        import hashlib

        import sentry_sdk  # type: ignore[import-untyped]

        sentry_sdk.set_user(
            {
                "id": user_id,
                # Don't send raw email to Sentry
                "email_hash": hashlib.sha256(email.encode()).hexdigest() if email else None,
            }
        )
    except (ImportError, AttributeError):
        pass  # Sentry not available
