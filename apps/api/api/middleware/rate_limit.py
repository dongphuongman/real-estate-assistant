"""
IP-based sliding window rate limiting middleware.

Enforces configurable request-per-minute limits with stricter
bounds on authentication endpoints. Returns 429 with Retry-After
header when exceeded.
"""

import asyncio
import time
from collections import defaultdict
from typing import Any

from fastapi import FastAPI, Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from config.settings import get_settings

# Default RPM for general endpoints
DEFAULT_RPM = 600

# Stricter limits for auth endpoints (requests per minute)
AUTH_PATHS = {
    "/api/v1/auth/login": 20,
    "/api/v1/auth/register": 10,
    "/api/v1/auth/forgot-password": 5,
    "/api/v1/auth/reset-password": 5,
    "/api/v1/auth/verify-email": 10,
}

# Window size in seconds
WINDOW_SECONDS = 60


class SlidingWindowRateLimiter:
    """In-memory sliding window rate limiter keyed by client IP."""

    def __init__(self, default_rpm: int = DEFAULT_RPM) -> None:
        self.default_rpm = default_rpm
        # ip -> list of request timestamps
        self._requests: dict[str, list[float]] = defaultdict(list)
        self._lock = asyncio.Lock()

    async def is_allowed(self, key: str, limit: int) -> tuple[bool, int]:
        """Check if request is allowed. Returns (allowed, retry_after_seconds)."""
        now = time.monotonic()
        cutoff = now - WINDOW_SECONDS

        async with self._lock:
            # Prune old entries
            self._requests[key] = [t for t in self._requests[key] if t > cutoff]

            if len(self._requests[key]) >= limit:
                # Calculate retry-after from oldest request in window
                oldest = self._requests[key][0]
                retry_after = int(oldest + WINDOW_SECONDS - now) + 1
                return False, max(retry_after, 1)

            self._requests[key].append(now)
            return True, 0

    def get_stats(self) -> dict[str, Any]:
        """Return current stats for metrics."""
        return {
            "enabled": True,
            "default_rpm": self.default_rpm,
            "tracked_ips": len(self._requests),
        }

    async def cleanup(self) -> None:
        """Remove expired entries (call periodically or on shutdown)."""
        now = time.monotonic()
        cutoff = now - WINDOW_SECONDS
        async with self._lock:
            expired_keys = [k for k, v in self._requests.items() if all(t <= cutoff for t in v)]
            for k in expired_keys:
                del self._requests[k]


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Middleware that enforces rate limits per client IP."""

    def __init__(self, app: Any, limiter: SlidingWindowRateLimiter) -> None:
        super().__init__(app)
        self.limiter = limiter

    async def dispatch(self, request: Request, call_next: Any) -> Response:
        settings = get_settings()
        if not settings.api_rate_limit_enabled:
            return await call_next(request)

        # Skip rate limiting for health and metrics endpoints
        path = request.url.path
        if path in ("/health", "/metrics", "/docs", "/openapi.json", "/redoc"):
            return await call_next(request)

        # Determine limit for this path
        limit = self._get_limit_for_path(path)

        # Use client IP as key (behind proxy: X-Forwarded-For, else direct)
        client_ip = (
            request.headers.get(
                "x-forwarded-for", request.client.host if request.client else "unknown"
            )
            .split(",")[0]
            .strip()
        )

        allowed, retry_after = await self.limiter.is_allowed(client_ip, limit)

        if not allowed:
            return Response(
                content=f'{{"detail":"Rate limit exceeded. Retry after {retry_after}s."}}',
                status_code=429,
                headers={
                    "Retry-After": str(retry_after),
                    "Content-Type": "application/json",
                    "X-RateLimit-Limit": str(limit),
                    "X-RateLimit-Remaining": "0",
                },
            )

        response = await call_next(request)

        # Add rate limit headers to successful responses
        response.headers["X-RateLimit-Limit"] = str(limit)
        remaining = max(0, limit - 1)  # Approximate
        response.headers["X-RateLimit-Remaining"] = str(remaining)

        return response

    def _get_limit_for_path(self, path: str) -> int:
        """Return the rate limit for a given path."""
        for auth_path, limit in AUTH_PATHS.items():
            if path.startswith(auth_path):
                return limit
        return self.limiter.default_rpm


def add_rate_limit_middleware(app: FastAPI) -> None:
    """Add rate limiting middleware to the FastAPI application."""
    settings = get_settings()
    rpm = settings.api_rate_limit_rpm if settings.api_rate_limit_enabled else 999999
    limiter = SlidingWindowRateLimiter(default_rpm=rpm)
    app.state.rate_limiter = limiter
    app.add_middleware(RateLimitMiddleware, limiter=limiter)
