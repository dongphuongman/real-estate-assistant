import hashlib
import logging
import re
import time
import uuid
from collections import defaultdict, deque
from threading import Lock

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

REQUEST_ID_HEADER = "X-Request-ID"
_REQUEST_ID_RE = re.compile(r"^[A-Za-z0-9._-]{1,128}$")

_RATE_LIMIT_EXCLUDED_PREFIXES = (
    "/health",
    "/docs",
    "/redoc",
    "/openapi.json",
)


class RateLimiter:
    def __init__(self, max_requests: int = 600, window_seconds: int = 60) -> None:
        self._max_requests = max(1, int(max_requests))
        self._window_seconds = max(1, int(window_seconds))
        self._lock = Lock()
        self._events: dict[str, deque[float]] = defaultdict(deque)

    def configure(self, max_requests: int, window_seconds: int) -> None:
        with self._lock:
            self._max_requests = max(1, int(max_requests))
            self._window_seconds = max(1, int(window_seconds))

    def reset(self) -> None:
        with self._lock:
            self._events.clear()

    def check(self, key: str, now: float | None = None) -> tuple[bool, int, int, int]:
        ts = time.time() if now is None else now
        key = key or "anonymous"

        with self._lock:
            window_start = ts - self._window_seconds
            q = self._events[key]

            while q and q[0] <= window_start:
                q.popleft()

            if len(q) >= self._max_requests:
                oldest = q[0] if q else ts
                reset_in = max(1, int((oldest + self._window_seconds) - ts))
                return False, self._max_requests, 0, reset_in

            q.append(ts)
            remaining = max(0, self._max_requests - len(q))
            oldest = q[0] if q else ts
            reset_in = max(1, int((oldest + self._window_seconds) - ts))
            return True, self._max_requests, remaining, reset_in


def normalize_request_id(value: str | None) -> str | None:
    if value is None:
        return None
    candidate = value.strip()
    if not candidate:
        return None
    if _REQUEST_ID_RE.fullmatch(candidate) is None:
        return None
    return candidate


def generate_request_id() -> str:
    return uuid.uuid4().hex


def client_id_from_api_key(api_key: str | None) -> str | None:
    if not api_key:
        return None
    digest = hashlib.sha256(api_key.encode("utf-8")).hexdigest()
    return digest[:12]


def add_observability(app: FastAPI, logger: logging.Logger) -> None:
    limiter = RateLimiter()
    app.state.rate_limiter = limiter
    app.state.metrics: dict[str, int] = {}

    @app.middleware("http")
    async def _request_id_middleware(request: Request, call_next):
        from config.settings import get_settings

        settings = get_settings()

        request_id = normalize_request_id(request.headers.get(REQUEST_ID_HEADER))
        if request_id is None:
            request_id = generate_request_id()

        request.state.request_id = request_id
        response_headers = {REQUEST_ID_HEADER: request_id}

        if getattr(settings, "api_rate_limit_enabled", False):
            path = request.url.path
            excluded = _RATE_LIMIT_EXCLUDED_PREFIXES
            if path.startswith("/api/v1") and not path.startswith(excluded):
                api_key = request.headers.get("X-API-Key")
                client_id = client_id_from_api_key(api_key) or "anonymous"
                rpm = int(getattr(settings, "api_rate_limit_rpm", 600))
                limiter.configure(max_requests=rpm, window_seconds=60)

                allowed, limit, remaining, reset_in = limiter.check(client_id)
                response_headers.update(
                    {
                        "X-RateLimit-Limit": str(limit),
                        "X-RateLimit-Remaining": str(remaining),
                        "X-RateLimit-Reset": str(reset_in),
                    }
                )

                if not allowed:
                    response_headers["Retry-After"] = str(reset_in)
                    logger.info(
                        "api_rate_limited",
                        extra={
                            "event": "api_rate_limited",
                            "request_id": request_id,
                            "client_id": client_id,
                            "method": request.method,
                            "path": path,
                            "status": 429,
                            "duration_ms": 0.0,
                        },
                    )
                    return JSONResponse(
                        status_code=429,
                        content={"detail": "Rate limit exceeded"},
                        headers=response_headers,
                    )

        start = time.perf_counter()
        response = await call_next(request)
        elapsed_ms = (time.perf_counter() - start) * 1000.0

        for k, v in response_headers.items():
            response.headers[k] = v

        client_id = client_id_from_api_key(request.headers.get("X-API-Key"))
        logger.info(
            "api_request",
            extra={
                "event": "api_request",
                "request_id": request_id,
                "client_id": (client_id or "-"),
                "method": request.method,
                "path": request.url.path,
                "status": getattr(response, "status_code", "-"),
                "duration_ms": float(elapsed_ms),
            },
        )

        key = f"{request.method} {request.url.path}"
        app.state.metrics[key] = int(app.state.metrics.get(key, 0)) + 1

        return response
