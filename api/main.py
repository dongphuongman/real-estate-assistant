import logging
import os

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.auth import get_api_key
from api.dependencies import get_vector_store
from api.models import HealthCheck
from api.observability import add_observability
from api.routers import admin, auth, chat, exports, prompt_templates, search, tools
from api.routers import rag as rag_router
from api.routers import settings as settings_router
from config.settings import get_settings
from notifications.email_service import (
    EmailConfig,
    EmailProvider,
    EmailService,
    EmailServiceFactory,
)
from notifications.scheduler import NotificationScheduler
from notifications.uptime_monitor import (
    UptimeMonitor,
    UptimeMonitorConfig,
    make_http_checker,
)
from utils.json_logging import configure_json_logging

configure_json_logging(logging.INFO)
logger = logging.getLogger(__name__)

settings = get_settings()

app = FastAPI(
    title=settings.app_title,
    version=settings.version,
    description="AI Real Estate Assistant API V4",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

add_observability(app, logger)

# Global scheduler instance
scheduler = None


@app.on_event("startup")
async def startup_event():
    """Initialize application services on startup."""
    global scheduler

    # 1. Initialize Vector Store
    logger.info("Initializing Vector Store...")
    vector_store = get_vector_store()
    if not vector_store:
        logger.warning(
            "Vector Store could not be initialized. "
            "Notifications relying on vector search will be disabled."
        )

    # 2. Initialize Email Service
    logger.info("Initializing Email Service...")
    email_service = EmailServiceFactory.create_from_env()

    if not email_service:
        logger.warning(
            "No email configuration found in environment. "
            "Using dummy service (emails will not be sent)."
        )
        # Create dummy service for scheduler to function without crashing
        dummy_config = EmailConfig(
            provider=EmailProvider.CUSTOM,
            smtp_server="localhost",
            smtp_port=1025,
            username="dummy",
            password="dummy",
            from_email="noreply@example.com",
        )
        email_service = EmailService(dummy_config)

    # 3. Initialize and Start Scheduler
    logger.info("Starting Notification Scheduler...")
    try:
        scheduler = NotificationScheduler(
            email_service=email_service,
            vector_store=vector_store,
            poll_interval_seconds=60,
        )
        scheduler.start()
        app.state.scheduler = scheduler
        logger.info("Notification Scheduler started successfully.")
    except Exception as e:
        logger.error(f"Failed to start Notification Scheduler: {e}")

    # 4. Initialize Uptime Monitor (optional via env)
    try:
        enabled_raw = os.getenv("UPTIME_MONITOR_ENABLED", "false").strip().lower()
        enabled = enabled_raw in {"1", "true", "yes", "y", "on"}
        if enabled and email_service:
            health_url = os.getenv("UPTIME_MONITOR_HEALTH_URL", "http://localhost:8000/health").strip()
            to_email = os.getenv("UPTIME_MONITOR_EMAIL_TO", "ops@example.com").strip() or "ops@example.com"
            interval = float(os.getenv("UPTIME_MONITOR_INTERVAL", "60").strip() or "60")
            threshold = int(os.getenv("UPTIME_MONITOR_FAIL_THRESHOLD", "3").strip() or "3")
            cooldown = float(os.getenv("UPTIME_MONITOR_COOLDOWN_SECONDS", "1800").strip() or "1800")
            checker = make_http_checker(health_url, timeout=3.0)
            mon_cfg = UptimeMonitorConfig(
                interval_seconds=interval,
                fail_threshold=threshold,
                alert_cooldown_seconds=cooldown,
                to_email=to_email,
            )
            uptime_monitor = UptimeMonitor(checker=checker, email_service=email_service, config=mon_cfg, logger=logger)
            uptime_monitor.start()
            app.state.uptime_monitor = uptime_monitor
            logger.info("Uptime Monitor started url=%s to=%s interval=%s", health_url, to_email, interval)
    except Exception as e:
        logger.error(f"Failed to start Uptime Monitor: {e}")


@app.on_event("shutdown")
async def shutdown_event():
    """Clean up resources on shutdown."""
    if scheduler:
        logger.info("Stopping Notification Scheduler...")
        scheduler.stop()
        logger.info("Notification Scheduler stopped.")
    mon = getattr(app.state, "uptime_monitor", None)
    if mon:
        logger.info("Stopping Uptime Monitor...")
        mon.stop()
        logger.info("Uptime Monitor stopped.")


# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=get_settings().cors_allow_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include Routers
app.include_router(search.router, prefix="/api/v1", dependencies=[Depends(get_api_key)])
app.include_router(chat.router, prefix="/api/v1", dependencies=[Depends(get_api_key)])
app.include_router(rag_router.router, prefix="/api/v1", dependencies=[Depends(get_api_key)])
app.include_router(
    settings_router.router, prefix="/api/v1", dependencies=[Depends(get_api_key)]
)
app.include_router(tools.router, prefix="/api/v1", dependencies=[Depends(get_api_key)])
app.include_router(prompt_templates.router, prefix="/api/v1", dependencies=[Depends(get_api_key)])
app.include_router(admin.router, prefix="/api/v1", dependencies=[Depends(get_api_key)])
app.include_router(
    exports.router, prefix="/api/v1", dependencies=[Depends(get_api_key)]
)
app.include_router(auth.router, prefix="/api/v1")


@app.get("/health", response_model=HealthCheck, tags=["System"])
async def health_check():
    """
    Health check endpoint to verify API status.
    """
    return HealthCheck(status="healthy", version=settings.version)


@app.get("/api/v1/verify-auth", dependencies=[Depends(get_api_key)], tags=["Auth"])
async def verify_auth():
    """
    Verify API key authentication.
    """
    return {"message": "Authenticated successfully", "valid": True}
