import hashlib
import logging
import re
import time
import uuid

from fastapi import FastAPI, Request

REQUEST_ID_HEADER = "X-Request-ID"
_REQUEST_ID_RE = re.compile(r"^[A-Za-z0-9._-]{1,128}$")


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
    @app.middleware("http")
    async def _request_id_middleware(request: Request, call_next):
        request_id = normalize_request_id(request.headers.get(REQUEST_ID_HEADER))
        if request_id is None:
            request_id = generate_request_id()

        request.state.request_id = request_id

        start = time.perf_counter()
        response = await call_next(request)
        elapsed_ms = (time.perf_counter() - start) * 1000.0

        response.headers[REQUEST_ID_HEADER] = request_id

        client_id = client_id_from_api_key(request.headers.get("X-API-Key"))
        logger.info(
            "api_request request_id=%s client_id=%s method=%s path=%s status=%s duration_ms=%.2f",
            request_id,
            client_id or "-",
            request.method,
            request.url.path,
            getattr(response, "status_code", "-"),
            elapsed_ms,
        )

        return response
