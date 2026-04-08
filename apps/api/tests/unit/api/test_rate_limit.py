"""
Tests for rate limiting middleware (Task #62).
"""

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from api.middleware.rate_limit import (
    RateLimitMiddleware,
    SlidingWindowRateLimiter,
    add_rate_limit_middleware,
)


class TestSlidingWindowRateLimiter:
    """Test the sliding window rate limiter core logic."""

    @pytest.mark.asyncio
    async def test_allows_within_limit(self):
        limiter = SlidingWindowRateLimiter(default_rpm=5)
        for _ in range(5):
            allowed, retry = await limiter.is_allowed("1.2.3.4", 5)
            assert allowed is True
            assert retry == 0

    @pytest.mark.asyncio
    async def test_blocks_over_limit(self):
        limiter = SlidingWindowRateLimiter(default_rpm=3)
        for _ in range(3):
            await limiter.is_allowed("1.2.3.4", 3)
        allowed, retry = await limiter.is_allowed("1.2.3.4", 3)
        assert allowed is False
        assert retry > 0

    @pytest.mark.asyncio
    async def test_different_ips_independent(self):
        limiter = SlidingWindowRateLimiter(default_rpm=2)
        await limiter.is_allowed("1.1.1.1", 2)
        await limiter.is_allowed("1.1.1.1", 2)
        # IP 2 should still be allowed
        allowed, _ = await limiter.is_allowed("2.2.2.2", 2)
        assert allowed is True

    @pytest.mark.asyncio
    async def test_get_stats(self):
        limiter = SlidingWindowRateLimiter(default_rpm=100)
        stats = limiter.get_stats()
        assert stats["enabled"] is True
        assert stats["default_rpm"] == 100
        assert stats["tracked_ips"] == 0


class TestRateLimitMiddleware:
    """Test the middleware integration with FastAPI."""

    @pytest.fixture
    async def rate_limited_client(self):
        app = FastAPI()
        limiter = SlidingWindowRateLimiter(default_rpm=5)
        app.state.rate_limiter = limiter
        app.add_middleware(RateLimitMiddleware, limiter=limiter)

        @app.get("/test")
        async def test_endpoint():
            return {"ok": True}

        @app.get("/health")
        async def health():
            return {"status": "ok"}

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            yield client

    @pytest.mark.asyncio
    async def test_allows_requests_within_limit(self, rate_limited_client):
        for _ in range(5):
            resp = await rate_limited_client.get("/test")
            assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_returns_429_over_limit(self, rate_limited_client):
        for _ in range(5):
            await rate_limited_client.get("/test")
        resp = await rate_limited_client.get("/test")
        assert resp.status_code == 429
        assert "Retry-After" in resp.headers
        assert resp.headers["X-RateLimit-Remaining"] == "0"

    @pytest.mark.asyncio
    async def test_health_endpoint_not_rate_limited(self, rate_limited_client):
        """Health endpoint should bypass rate limiting."""
        for _ in range(10):
            resp = await rate_limited_client.get("/health")
            assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_rate_limit_headers_on_success(self, rate_limited_client):
        resp = await rate_limited_client.get("/test")
        assert "X-RateLimit-Limit" in resp.headers
        assert resp.headers["X-RateLimit-Limit"] == "5"

    @pytest.mark.asyncio
    async def test_429_response_is_json(self, rate_limited_client):
        for _ in range(5):
            await rate_limited_client.get("/test")
        resp = await rate_limited_client.get("/test")
        assert resp.status_code == 429
        body = resp.json()
        assert "detail" in body

    @pytest.mark.asyncio
    async def test_add_rate_limit_middleware(self):
        """Test the add_rate_limit_middleware helper."""
        app = FastAPI()
        add_rate_limit_middleware(app)
        assert hasattr(app.state, "rate_limiter")
        assert app.state.rate_limiter.default_rpm > 0
        assert app.state.rate_limiter.get_stats()["enabled"] is True
