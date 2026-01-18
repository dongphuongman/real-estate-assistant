from unittest.mock import patch

import pytest
from fastapi import HTTPException

from api.auth import get_api_key
from api.observability import (
    RateLimiter,
    client_id_from_api_key,
    generate_request_id,
    normalize_request_id,
)
from config.settings import AppSettings


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


def test_rate_limiter_allows_requests_within_window():
    limiter = RateLimiter(max_requests=2, window_seconds=60)

    allowed1, limit1, remaining1, reset1 = limiter.check("client", now=1000.0)
    allowed2, limit2, remaining2, reset2 = limiter.check("client", now=1001.0)

    assert allowed1 is True
    assert allowed2 is True
    assert limit1 == 2
    assert limit2 == 2
    assert remaining1 == 1
    assert remaining2 == 0
    assert reset1 >= 1
    assert reset2 >= 1


def test_rate_limiter_blocks_when_exceeded_and_recovers_after_window():
    limiter = RateLimiter(max_requests=2, window_seconds=60)

    limiter.check("client", now=1000.0)
    limiter.check("client", now=1001.0)

    allowed3, limit3, remaining3, reset3 = limiter.check("client", now=1002.0)
    assert allowed3 is False
    assert limit3 == 2
    assert remaining3 == 0
    assert reset3 >= 1

    allowed4, _limit4, remaining4, _reset4 = limiter.check("client", now=1061.0)
    assert allowed4 is True
    assert remaining4 == 1
