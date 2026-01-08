from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from api.auth import get_api_key
from api.models import HealthCheck
from api.routers import search
from config.settings import get_settings

settings = get_settings()

app = FastAPI(
    title=settings.app_title,
    version=settings.version,
    description="AI Real Estate Assistant API V4",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)

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
