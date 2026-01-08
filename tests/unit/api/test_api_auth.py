import pytest
from fastapi import HTTPException
from api.auth import get_api_key
from config.settings import AppSettings
from unittest.mock import patch

@pytest.mark.asyncio
async def test_get_api_key_valid():
    """Test valid API key acceptance."""
    key = "test-key"
    with patch("api.auth.get_settings") as mock_settings:
        mock_settings.return_value = AppSettings(api_access_key=key)
        result = await get_api_key(api_key_header=key)
        assert result == key

@pytest.mark.asyncio
async def test_get_api_key_invalid():
    """Test invalid API key rejection."""
    key = "test-key"
    with patch("api.auth.get_settings") as mock_settings:
        mock_settings.return_value = AppSettings(api_access_key=key)
        with pytest.raises(HTTPException) as exc:
            await get_api_key(api_key_header="wrong-key")
        assert exc.value.status_code == 403

@pytest.mark.asyncio
async def test_get_api_key_missing():
    """Test missing API key handling."""
    with pytest.raises(HTTPException) as exc:
        await get_api_key(api_key_header=None)
    assert exc.value.status_code == 401
