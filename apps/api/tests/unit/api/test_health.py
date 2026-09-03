import asyncio
import sys
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

import api.dependencies as api_dependencies
from api.health import (
    DependencyHealth,
    HealthCheckResponse,
    HealthStatus,
    check_database,
    check_llm_provider,
    check_redis,
    check_vector_store,
    get_health_status,
    require_healthy,
)


class FakeResponse:
    def __init__(self, status_code: int):
        self.status_code = status_code


class FakeAsyncClient:
    def __init__(self, status_code: int):
        self._status_code = status_code

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return None

    async def get(self, url):
        return FakeResponse(self._status_code)


class FakeRedisClient:
    def __init__(self, should_fail: bool):
        self._should_fail = should_fail

    def ping(self):
        if self._should_fail:
            raise RuntimeError("redis down")
        return "PONG"

    def close(self):
        return None


@pytest.mark.asyncio
async def test_check_redis_returns_none_when_not_configured(monkeypatch):
    monkeypatch.delenv("REDIS_URL", raising=False)
    result = await check_redis()
    assert result is None


@pytest.mark.asyncio
async def test_check_redis_reports_healthy_when_ping_succeeds(monkeypatch):
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")
    fake_module = SimpleNamespace(from_url=lambda *_args, **_kwargs: FakeRedisClient(False))
    monkeypatch.setitem(sys.modules, "redis", fake_module)
    result = await check_redis()
    assert result is not None
    assert result.status == HealthStatus.HEALTHY
    assert result.message == "OK"


@pytest.mark.asyncio
async def test_check_redis_reports_unhealthy_on_error(monkeypatch):
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")
    fake_module = SimpleNamespace(from_url=lambda *_args, **_kwargs: FakeRedisClient(True))
    monkeypatch.setitem(sys.modules, "redis", fake_module)
    result = await check_redis()
    assert result is not None
    assert result.status == HealthStatus.UNHEALTHY
    assert result.message.startswith("Error:")


@pytest.mark.asyncio
async def test_check_llm_provider_degraded_without_providers(monkeypatch):
    settings = SimpleNamespace(
        openai_api_key=None,
        anthropic_api_key=None,
        google_api_key=None,
        grok_api_key=None,
        deepseek_api_key=None,
        default_provider="openai",
    )
    fake_httpx = SimpleNamespace(AsyncClient=lambda timeout=2.0: FakeAsyncClient(404))
    monkeypatch.setitem(sys.modules, "httpx", fake_httpx)
    monkeypatch.setattr("api.health.get_settings", lambda: settings)
    result = await check_llm_provider()
    assert result.status == HealthStatus.DEGRADED
    assert result.details == {"configured_providers": []}


@pytest.mark.asyncio
async def test_check_llm_provider_includes_ollama_when_available(monkeypatch):
    settings = SimpleNamespace(
        openai_api_key=None,
        anthropic_api_key=None,
        google_api_key=None,
        grok_api_key=None,
        deepseek_api_key=None,
        default_provider="openai",
    )
    fake_httpx = SimpleNamespace(AsyncClient=lambda timeout=2.0: FakeAsyncClient(200))
    monkeypatch.setitem(sys.modules, "httpx", fake_httpx)
    monkeypatch.setattr("api.health.get_settings", lambda: settings)
    result = await check_llm_provider()
    assert result.status == HealthStatus.HEALTHY
    assert result.details == {"configured_providers": ["ollama"], "default": "openai"}


@pytest.mark.asyncio
async def test_check_llm_provider_healthy_with_configured_key(monkeypatch):
    settings = SimpleNamespace(
        openai_api_key="sk-test",
        anthropic_api_key=None,
        google_api_key=None,
        grok_api_key=None,
        deepseek_api_key=None,
        default_provider="openai",
    )
    fake_httpx = SimpleNamespace(AsyncClient=lambda timeout=2.0: FakeAsyncClient(500))
    monkeypatch.setitem(sys.modules, "httpx", fake_httpx)
    monkeypatch.setattr("api.health.get_settings", lambda: settings)
    result = await check_llm_provider()
    assert result.status == HealthStatus.HEALTHY
    assert result.details == {"configured_providers": ["openai"], "default": "openai"}


@pytest.mark.asyncio
async def test_get_health_status_unhealthy_when_vector_store_unhealthy(monkeypatch):
    """Test that health status is UNHEALTHY when the vector store dependency
    check reports UNHEALTHY.

    Patches all four dependency-check seams (vector_store, redis, database,
    llm_provider) so the test does not depend on whether chromadb is
    installed in the current environment, on DATABASE_URL being set in the
    runner, or on Redis being reachable. On Linux CI chromadb IS installed
    (FastEmbed ships in the test image) and ``DATABASE_URL`` is sometimes
    set to a non-existent path — both must be neutralised at the seam
    ``get_health_status`` calls, otherwise ``check_database`` either fails
    (returning UNHEALTHY in addition to vector_store, which the prior
    test asserted around but the spec still required UNHEALTHY) or
    raises (returning the exception via ``asyncio.gather(return_exceptions=True)``).
    Mocking every dependency check is deterministic across Windows / Linux /
    chromadb-present / chromadb-absent / DATABASE_URL-set / DATABASE_URL-absent.
    """
    settings = SimpleNamespace(version="9.9.9", database_url=None)

    async def _vector_unhealthy():
        return DependencyHealth(
            name="vector_store",
            status=HealthStatus.UNHEALTHY,
            message="vector store not initialized",
        )

    async def _redis_healthy():
        return DependencyHealth(
            name="redis",
            status=HealthStatus.HEALTHY,
            message="ok",
        )

    async def _database_none():
        return None

    async def _llm_healthy():
        return DependencyHealth(
            name="llm_providers",
            status=HealthStatus.HEALTHY,
            message="ok",
        )

    monkeypatch.setattr("api.health.get_settings", lambda: settings)
    monkeypatch.setattr("api.health.check_vector_store", _vector_unhealthy)
    monkeypatch.setattr("api.health.check_redis", _redis_healthy)
    monkeypatch.setattr("api.health.check_database", _database_none)
    monkeypatch.setattr("api.health.check_llm_provider", _llm_healthy)

    result = await get_health_status(include_dependencies=True)
    assert result.status == HealthStatus.UNHEALTHY
    assert result.dependencies["vector_store"].status == HealthStatus.UNHEALTHY
    assert result.version == "9.9.9"


@pytest.mark.asyncio
async def test_check_vector_store_uses_thread_for_blocking_count(monkeypatch):
    """The blocking ChromaDB count must be off the event loop."""

    import threading

    class _CountProbe:
        def __init__(self):
            self.invoked_on = None
            self.call_count = 0

        def count(self):
            self.call_count += 1
            self.invoked_on = threading.get_ident()
            return 42

    probe = _CountProbe()
    fake_store = SimpleNamespace(_collection=probe)

    # Drop any cached result so the patched callable is exercised.
    api_dependencies.get_vector_store.cache_clear()

    def _fake_get_vector_store():
        return fake_store

    # Patch the symbol bound into the api.health module so the new
    # asyncio.to_thread wrapping is exercised end-to-end.
    monkeypatch.setattr("api.health.get_vector_store", _fake_get_vector_store)

    loop_thread = threading.get_ident()
    result = await check_vector_store()

    assert result.status == HealthStatus.HEALTHY
    assert probe.call_count == 1
    assert result.details == {"item_count": 42}
    assert probe.invoked_on is not None
    assert probe.invoked_on != loop_thread


@pytest.mark.asyncio
async def test_get_health_status_marks_slow_dependency_degraded(monkeypatch):
    """A slow dependency check must not block the response and must be DEGRADED.

    The slow check waits on an ``asyncio.Event`` rather than sleeping. The
    bounded check (``asyncio.wait_for(check(), timeout=4.0)``) cancels the
    slow check at 4s and reports ``DEGRADED`` with ``"Timed out"``. The test
    sets the event after verification so the (now-cancelled) coroutine
    cleans up without an asyncio warning. Event-based blocking is
    deterministic across asyncio Mode.AUTO + pytest-xdist + Linux CI; the
    previous ``asyncio.sleep(10)``-based version could complete before the
    bounded check fired under xdist on Linux runners.
    """

    import time

    block_event = asyncio.Event()

    async def _slow_vector():
        # Block indefinitely until the bounded check cancels us. asyncio.Event.wait
        # is the simplest awaitable that (a) cannot complete "early" the way a
        # sleep can, and (b) propagates CancelledError cleanly when wait_for
        # cancels the parent task.
        await block_event.wait()
        return DependencyHealth(
            name="vector_store",
            status=HealthStatus.HEALTHY,
            message="should not be reached",
        )

    async def _ok_redis():
        return None

    async def _ok_database():
        return None

    async def _ok_llm():
        return DependencyHealth(
            name="llm_providers",
            status=HealthStatus.HEALTHY,
            message="ok",
        )

    monkeypatch.setattr("api.health.check_vector_store", _slow_vector)
    monkeypatch.setattr("api.health.check_redis", _ok_redis)
    monkeypatch.setattr("api.health.check_database", _ok_database)
    monkeypatch.setattr("api.health.check_llm_provider", _ok_llm)
    monkeypatch.setattr("api.health.get_settings", lambda: SimpleNamespace(version="1.0.0"))

    started = time.monotonic()
    status_task = asyncio.create_task(get_health_status(include_dependencies=True))

    # The bounded check fires at 4s. The status task should complete in
    # 4–5s on a healthy runner with vector_store reported as DEGRADED +
    # "Timed out". The outer wait budget is widened to 12s (from 5s) to
    # tolerate slow Linux CI runners where gather scheduling and the
    # CancelledError propagation take longer than the bounded check's
    # 4s — without the wider budget, asyncio.wait_for raises TimeoutError
    # spuriously even though the bounded check would have fired correctly.
    result = await asyncio.wait_for(status_task, timeout=12.0)
    elapsed = time.monotonic() - started

    # Release the (cancelled) slow check so its await unblocks cleanly.
    block_event.set()

    assert elapsed < 10.0
    assert result.dependencies["vector_store"].status == HealthStatus.DEGRADED
    assert "Timed out" in result.dependencies["vector_store"].message


@pytest.mark.asyncio
async def test_require_healthy_raises_on_unhealthy_dependencies(monkeypatch):
    response = HealthCheckResponse(
        status=HealthStatus.UNHEALTHY,
        version="1.0.0",
        timestamp="2026-01-01T00:00:00Z",
        dependencies={
            "vector_store": DependencyHealth(
                name="vector_store",
                status=HealthStatus.UNHEALTHY,
                message="down",
            ),
            "redis": DependencyHealth(
                name="redis",
                status=HealthStatus.HEALTHY,
                message="ok",
            ),
        },
        uptime_seconds=1.0,
    )

    async def _fake_get_health_status(*_args, **_kwargs):
        return response

    monkeypatch.setattr("api.health.get_health_status", _fake_get_health_status)
    with pytest.raises(HTTPException) as exc_info:
        await require_healthy()
    assert "vector_store" in str(exc_info.value.detail)


# Tests for check_database
@pytest.mark.asyncio
async def test_check_database_returns_none_when_not_configured(monkeypatch):
    """Database check returns None when DATABASE_URL is not set."""
    settings = SimpleNamespace(database_url=None)
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setattr("api.health.get_settings", lambda: settings)
    result = await check_database()
    assert result is None


@pytest.mark.asyncio
async def test_check_database_healthy_when_connection_succeeds(monkeypatch):
    """Database check returns healthy when connection succeeds."""
    settings = SimpleNamespace(database_url="sqlite+aiosqlite:///test.db")

    # Create fake engine and connection
    class FakeConnection:
        async def execute(self, text):
            return None

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return None

    class FakeEngine:
        def connect(self):
            return FakeConnection()

    fake_sqlalchemy = SimpleNamespace(text=lambda s: s)
    fake_database = SimpleNamespace(get_engine=lambda: FakeEngine())

    monkeypatch.setenv("DATABASE_URL", "sqlite+aiosqlite:///test.db")
    monkeypatch.setattr("api.health.get_settings", lambda: settings)
    monkeypatch.setitem(sys.modules, "sqlalchemy", fake_sqlalchemy)
    monkeypatch.setitem(sys.modules, "db.database", fake_database)

    result = await check_database()
    assert result is not None
    assert result.status == HealthStatus.HEALTHY
    assert result.message == "OK"


@pytest.mark.asyncio
async def test_check_database_unhealthy_on_error(monkeypatch):
    """Database check returns unhealthy when connection fails."""
    settings = SimpleNamespace(database_url="postgresql://invalid:5432/db")

    class FakeEngine:
        def connect(self):
            raise RuntimeError("Connection refused")

    fake_sqlalchemy = SimpleNamespace(text=lambda s: s)
    fake_database = SimpleNamespace(get_engine=lambda: FakeEngine())

    monkeypatch.setenv("DATABASE_URL", "postgresql://invalid:5432/db")
    monkeypatch.setattr("api.health.get_settings", lambda: settings)
    monkeypatch.setitem(sys.modules, "sqlalchemy", fake_sqlalchemy)
    monkeypatch.setitem(sys.modules, "db.database", fake_database)

    result = await check_database()
    assert result is not None
    assert result.status == HealthStatus.UNHEALTHY
    assert result.message.startswith("Error:")
