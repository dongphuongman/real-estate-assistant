import re

from api.observability import (
    RateLimiter,
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

