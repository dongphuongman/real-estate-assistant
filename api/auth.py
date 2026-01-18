from fastapi import HTTPException, Security, status
from fastapi.security.api_key import APIKeyHeader

from config.settings import get_settings

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

async def get_api_key(api_key_header: str = Security(api_key_header)):
    """
    Validate API key from header.
    
    Args:
        api_key_header: API key from X-API-Key header
        
    Returns:
        The valid API key
        
    Raises:
        HTTPException: If key is invalid or missing
    """
    settings = get_settings()
    
    if not api_key_header:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing API Key"
        )
        
    if api_key_header == settings.api_access_key:
        if settings.environment.strip().lower() == "production" and settings.api_access_key == "dev-secret-key":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Invalid configuration"
            )
        return api_key_header
        
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Could not validate credentials"
    )
