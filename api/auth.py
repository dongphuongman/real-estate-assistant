import hmac

from fastapi import HTTPException, Security, status
from fastapi.security.api_key import APIKeyHeader

from config.settings import get_settings

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


def _is_valid_api_key(candidate: str, valid_keys: list[str]) -> bool:
    for key in valid_keys:
        if key and hmac.compare_digest(candidate, key):
            return True
    return False


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

    configured_keys = getattr(settings, "api_access_keys", None)
    if not isinstance(configured_keys, list):
        configured_keys = []

    if not configured_keys:
        configured_key = getattr(settings, "api_access_key", None)
        if isinstance(configured_key, str) and configured_key.strip():
            configured_keys = [configured_key.strip()]

    environment = str(getattr(settings, "environment", "") or "").strip().lower()

    if environment == "production":
        if not configured_keys or any(k == "dev-secret-key" for k in configured_keys):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Invalid configuration"
            )

    if _is_valid_api_key(api_key_header, configured_keys):
        return api_key_header
        
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Could not validate credentials"
    )
