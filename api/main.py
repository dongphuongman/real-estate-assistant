from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from api.auth import get_api_key
from api.models import HealthCheck
from api.routers import search, chat, tools, admin
from api.dependencies import get_vector_store
from config.settings import get_settings
from notifications.scheduler import NotificationScheduler
from notifications.email_service import EmailServiceFactory, EmailConfig, EmailProvider, EmailService
import logging
import os

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

settings = get_settings()

app = FastAPI(
    title=settings.app_title,
    version=settings.version,
    description="AI Real Estate Assistant API V4",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)

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
        logger.warning("Vector Store could not be initialized. Notifications relying on vector search will be disabled.")

    # 2. Initialize Email Service
    logger.info("Initializing Email Service...")
    email_service = EmailServiceFactory.create_from_env()
    
    if not email_service:
        logger.warning("No email configuration found in environment. Using dummy service (emails will not be sent).")
        # Create dummy service for scheduler to function without crashing
        dummy_config = EmailConfig(
            provider=EmailProvider.CUSTOM,
            smtp_server="localhost",
            smtp_port=1025,
            username="dummy",
            password="dummy",
            from_email="noreply@example.com"
        )
        email_service = EmailService(dummy_config)

    # 3. Initialize and Start Scheduler
    logger.info("Starting Notification Scheduler...")
    try:
        scheduler = NotificationScheduler(
            email_service=email_service,
            vector_store=vector_store,
            poll_interval_seconds=60
        )
        scheduler.start()
        app.state.scheduler = scheduler
        logger.info("Notification Scheduler started successfully.")
    except Exception as e:
        logger.error(f"Failed to start Notification Scheduler: {e}")

@app.on_event("shutdown")
async def shutdown_event():
    """Clean up resources on shutdown."""
    global scheduler
    if scheduler:
        logger.info("Stopping Notification Scheduler...")
        scheduler.stop()
        logger.info("Notification Scheduler stopped.")

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include Routers
app.include_router(
    search.router,
    prefix="/api/v1",
    dependencies=[Depends(get_api_key)]
)
app.include_router(
    chat.router,
    prefix="/api/v1",
    dependencies=[Depends(get_api_key)]
)
app.include_router(
    tools.router,
    prefix="/api/v1",
    dependencies=[Depends(get_api_key)]
)
app.include_router(
    admin.router,
    prefix="/api/v1",
    dependencies=[Depends(get_api_key)]
)

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
