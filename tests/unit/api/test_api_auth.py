import pytest
from fastapi import HTTPException
from api.auth import get_api_key
from api.observability import (
    client_id_from_api_key,
    generate_request_id,
    normalize_request_id,
)
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


def test_normalize_request_id_accepts_valid_values():
    assert normalize_request_id("abc-123_DEF.ghi") == "abc-123_DEF.ghi"
    assert normalize_request_id("   abc-123   ") == "abc-123"


def test_normalize_request_id_rejects_invalid_values():
    assert normalize_request_id(None) is None
    assert normalize_request_id("") is None
    assert normalize_request_id("   ") is None
    assert normalize_request_id("has space") is None
    assert normalize_request_id("x" * 129) is None


def test_generate_request_id_returns_nonempty_hex():
    rid = generate_request_id()
    assert isinstance(rid, str)
    assert len(rid) == 32
    int(rid, 16)


def test_client_id_from_api_key_is_stable_and_uniqueish():
    assert client_id_from_api_key(None) is None
    assert client_id_from_api_key("") is None

    a1 = client_id_from_api_key("key-a")
    a2 = client_id_from_api_key("key-a")
    b1 = client_id_from_api_key("key-b")

    assert a1 == a2
    assert a1 != b1
    assert len(a1) == 12
