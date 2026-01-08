from pydantic import BaseModel

class HealthCheck(BaseModel):
    """Health check response model."""
    status: str
    version: str
