import asyncio
import logging
import os
import signal

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.auth import get_api_key
from api.dependencies import get_vector_store
from api.health import get_git_info, get_health_status
from api.middleware.request_size import add_request_size_limits
from api.middleware.security import add_security_headers
from api.observability import REQUEST_ID_HEADER, add_observability
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
add_security_headers(app)
add_request_size_limits(app)

# Global scheduler instance
scheduler = None

# Graceful shutdown configuration
SHUTDOWN_DRAIN_SECONDS = int(os.getenv("SHUTDOWN_DRAIN_SECONDS", "30"))
SHUTDOWN_MAX_WAIT_SECONDS = int(os.getenv("SHUTDOWN_MAX_WAIT_SECONDS", "60"))


@app.on_event("startup")
async def startup_event():
    """Initialize application services on startup and setup signal handlers."""
    global scheduler

    # Setup signal handlers for graceful shutdown (only in main thread)
    import threading
    if threading.current_thread() is threading.main_thread():
        for sig in (signal.SIGTERM, signal.SIGINT):
            if hasattr(signal, sig.name):
                signal.signal(sig, lambda s, f: None)  # Let FastAPI handle

    # 1. Initialize Vector Store
    logger.info("Initializing Vector Store...")
    vector_store = get_vector_store()
    if not vector_store:
        logger.warning(
            "Vector Store could not be initialized. "
            "Notifications relying on vector search will be disabled."
        )
    app.state.vector_store = vector_store

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
    """
    Clean up resources on shutdown with graceful drain period.

    This handler:
    1. Logs the shutdown initiation
    2. Waits for a drain period to allow in-flight requests to complete
    3. Stops background services (scheduler, monitors)
    4. Closes database/vector store connections
    5. Logs completion of shutdown
    """
    logger.info("Graceful shutdown initiated...")
    shutdown_start_time = asyncio.get_event_loop().time()

    # Step 1: Stop accepting new requests (handled by uvicorn)
    # We just need to drain in-flight requests during this period

    # Step 2: Stop Uptime Monitor first (doesn't depend on other services)
    mon = getattr(app.state, "uptime_monitor", None)
    if mon:
        logger.info("Stopping Uptime Monitor...")
        try:
            mon.stop()
            logger.info("Uptime Monitor stopped.")
        except Exception as e:
            logger.error(f"Error stopping Uptime Monitor: {e}")

    # Step 3: Stop Notification Scheduler
    if scheduler:
        logger.info("Stopping Notification Scheduler...")
        try:
            scheduler.stop()
            logger.info("Notification Scheduler stopped.")
        except Exception as e:
            logger.error(f"Error stopping Notification Scheduler: {e}")

    # Step 4: Wait for drain period to allow in-flight requests to complete
    if SHUTDOWN_DRAIN_SECONDS > 0:
        logger.info(f"Waiting {SHUTDOWN_DRAIN_SECONDS}s drain period for in-flight requests...")
        try:
            await asyncio.sleep(SHUTDOWN_DRAIN_SECONDS)
        except Exception as e:
            logger.warning(f"Drain period interrupted: {e}")

    # Step 5: Close vector store connection
    vector_store = getattr(app.state, "vector_store", None)
    if vector_store:
        logger.info("Closing Vector Store connection...")
        try:
            # ChromaDB doesn't need explicit closing, but if we had
            # a database connection we would close it here
            if hasattr(vector_store, "close"):
                await vector_store.close()
            logger.info("Vector Store connection closed.")
        except Exception as e:
            logger.error(f"Error closing Vector Store: {e}")

    # Step 6: Close rate limiter connections if using Redis
    rate_limiter = getattr(app.state, "rate_limiter", None)
    if rate_limiter and hasattr(rate_limiter, "_redis_client"):
        redis_client = rate_limiter._redis_client
        if redis_client:
            logger.info("Closing Redis connection...")
            try:
                await redis_client.aclose() if hasattr(redis_client, "aclose") else redis_client.close()
                logger.info("Redis connection closed.")
            except Exception as e:
                logger.error(f"Error closing Redis connection: {e}")

    shutdown_elapsed = asyncio.get_event_loop().time() - shutdown_start_time
    logger.info(f"Graceful shutdown completed in {shutdown_elapsed:.2f}s")


# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=get_settings().cors_allow_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=[REQUEST_ID_HEADER],
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


@app.get("/health", tags=["System"])
async def health_check(include_dependencies: bool = True):
    """
    Health check endpoint to verify API status.

    Args:
        include_dependencies: Whether to check dependency health (vector store, Redis, LLM providers)

    Returns:
        Comprehensive health status including dependencies
    """
    health = await get_health_status(include_dependencies=include_dependencies)

    # Convert to dict for JSON response
    response = {
        "status": health.status.value,
        "version": health.version,
        "timestamp": health.timestamp,
        "uptime_seconds": health.uptime_seconds,
    }

    if health.dependencies:
        response["dependencies"] = {
            name: {
                "status": dep.status.value,
                "message": dep.message,
                "latency_ms": dep.latency_ms,
            }
            for name, dep in health.dependencies.items()
        }

    # Add git info for production deployments
    git_info = get_git_info()
    if git_info.get("commit") != "unknown":
        response["git"] = git_info

    # Return appropriate HTTP status based on health
    from fastapi import status as http_status

    status_code = http_status.HTTP_200_OK
    if health.status.value == "unhealthy":
        status_code = http_status.HTTP_503_SERVICE_UNAVAILABLE
    elif health.status.value == "degraded":
        status_code = http_status.HTTP_200_OK  # Degraded is still 200, with info

    from fastapi.responses import JSONResponse

    return JSONResponse(content=response, status_code=status_code)


@app.get("/api/v1/verify-auth", dependencies=[Depends(get_api_key)], tags=["Auth"])
async def verify_auth():
    """
    Verify API key authentication.
    """
    return {"message": "Authenticated successfully", "valid": True}
