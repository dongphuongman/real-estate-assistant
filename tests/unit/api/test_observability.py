import logging
import re

from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.observability import (
    RateLimiter,
    add_observability,
    client_id_from_api_key,
    generate_request_id,
    normalize_request_id,
)


def test_rate_limiter_allows_within_limit():
    rl = RateLimiter(max_requests=2, window_seconds=60)
    ok1, limit1, rem1, reset1 = rl.check("c1", now=0.0)
    ok2, limit2, rem2, reset2 = rl.check("c1", now=0.0)
    assert ok1 is True and ok2 is True
    assert limit1 == 2 and limit2 == 2
    assert rem1 == 1 and rem2 == 0
    assert reset1 == 60 and reset2 == 60


def test_rate_limiter_blocks_when_exceeded():
    rl = RateLimiter(max_requests=1, window_seconds=60)
    ok1, _, _, _ = rl.check("c1", now=0.0)
    ok2, limit2, rem2, reset2 = rl.check("c1", now=0.0)
    assert ok1 is True
    assert ok2 is False
    assert limit2 == 1
    assert rem2 == 0
    assert reset2 == 60


def test_normalize_request_id_valid_and_invalid():
    assert normalize_request_id("abc-123._") == "abc-123._"
    assert normalize_request_id("  abc-123  ") == "abc-123"
    assert normalize_request_id("") is None
    assert normalize_request_id("   ") is None
    assert normalize_request_id("invalid*char") is None


def test_generate_request_id_format():
    rid = generate_request_id()
    assert isinstance(rid, str)
    assert bool(re.fullmatch(r"[0-9a-f]{32}", rid))


def test_client_id_from_api_key_hashing():
    h1 = client_id_from_api_key("key123")
    h2 = client_id_from_api_key("key123")
    h3 = client_id_from_api_key("other")
    assert h1 is not None and h2 is not None and h3 is not None
    assert len(h1) == 12
    assert h1 == h2
    assert h1 != h3


def test_request_id_header_replaced_when_invalid():
    app = FastAPI()
    add_observability(app, logger=logging.getLogger("test"))

    @app.get("/ping")
    def _ping():
        return {"ok": True}

    client = TestClient(app)
    invalid = "not ok!*"
    r = client.get("/ping", headers={"X-Request-ID": invalid})
    assert r.status_code == 200
    rid = r.headers.get("x-request-id")
    assert rid
    assert rid != invalid
    assert bool(re.fullmatch(r"[0-9a-f]{32}", rid))


def test_request_id_is_present_on_unhandled_exception_response():
    app = FastAPI()
    add_observability(app, logger=logging.getLogger("test"))

    @app.get("/boom")
    def _boom():
        raise RuntimeError("boom")

    client = TestClient(app)
    request_id = "test-req-500"
    r = client.get("/boom", headers={"X-Request-ID": request_id})
    assert r.status_code == 500
    assert r.headers.get("x-request-id") == request_id
    assert r.json()["detail"] == "Internal server error"


def test_rate_limiter_configure_updates_limits():
    rl = RateLimiter(max_requests=1, window_seconds=60)
    rl.configure(max_requests=5, window_seconds=120)

    ok1, limit1, _, _ = rl.check("c1", now=0.0)
    ok2, limit2, _, _ = rl.check("c1", now=0.0)
    ok3, limit3, _, _ = rl.check("c1", now=0.0)

    assert ok1 is True and ok2 is True and ok3 is True
    assert limit1 == 5 and limit2 == 5 and limit3 == 5


def test_rate_limiter_reset_clears_history():
    rl = RateLimiter(max_requests=1, window_seconds=60)
    rl.check("c1", now=0.0)
    ok2, _, _, _ = rl.check("c1", now=0.0)
    assert ok2 is False

    rl.reset()
    ok3, _, _, _ = rl.check("c1", now=0.0)
    assert ok3 is True


def test_rate_limiter_allows_anonymous_key():
    rl = RateLimiter(max_requests=1, window_seconds=60)
    ok, limit, remaining, reset = rl.check("", now=0.0)
    assert ok is True
    assert limit == 1
    assert remaining == 0
    assert reset == 60


def test_normalize_request_id_handles_none():
    assert normalize_request_id(None) is None


def test_client_id_from_api_key_handles_none():
    assert client_id_from_api_key(None) is None
    assert client_id_from_api_key("") is None
    # Whitespace-only keys still get hashed (function doesn't strip)
    result = client_id_from_api_key("  ")
    assert result is not None
    assert len(result) == 12


def test_add_observability_rate_limit_disabled_when_setting_false(monkeypatch):
    monkeypatch.setenv("API_RATE_LIMIT_ENABLED", "false")
    app = FastAPI()
    logger = logging.getLogger("test")
    add_observability(app, logger)

    @app.get("/ping")
    def _ping():
        return {"ok": True}

    client = TestClient(app)
    r = client.get("/ping")
    assert r.status_code == 200


def test_add_observability_sets_request_id_header():
    app = FastAPI()
    logger = logging.getLogger("test")
    add_observability(app, logger)

    @app.get("/ping")
    def _ping():
        return {"ok": True}

    client = TestClient(app)
    r = client.get("/ping")
    assert "x-request-id" in r.headers
