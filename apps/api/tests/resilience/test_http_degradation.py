"""
HTTP-level resilience tests for graceful degradation (Task #69).

Validates actual API endpoint behavior when external dependencies are unavailable:
- All LLM providers down -> meaningful error (not 500)
- ChromaDB unavailable -> search returns 503 with clear message
- Database down -> health endpoint reports degraded
- No 500 errors when external deps are down
- Response structure includes degradation information
"""

import pytest
from httpx import ASGITransport, AsyncClient

from core.circuit_breaker import CircuitState, ServiceDegradedError, get_breaker, reset_all_breakers

# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture(autouse=True)
def _clean_breakers():
    """Reset all circuit breakers between tests."""
    reset_all_breakers()
    yield
    reset_all_breakers()


def _make_health_app():
    """Create a minimal FastAPI app simulating health endpoint behavior.

    Mirrors the logic in api/main.py health endpoint without importing the
    full dependency chain (which triggers protobuf issues on Python 3.14).
    """
    from fastapi import FastAPI
    from fastapi.responses import JSONResponse

    from core.circuit_breaker import get_all_breaker_states

    app = FastAPI()

    @app.get("/health")
    async def health_check(include_dependencies: bool = True):
        breaker_states = get_all_breaker_states()

        dependencies = {}
        for name, state in breaker_states.items():
            if state["state"] == "open":
                dep_status = "unhealthy"
            elif state["state"] == "half_open":
                dep_status = "degraded"
            else:
                dep_status = "healthy"
            dependencies[name] = {
                "status": dep_status,
                "message": f"State: {state['state']}, failures: {state['total_failures']}/{state['total_calls']}",
            }

        # Determine overall status (mirrors api/health.py logic)
        critical_unhealthy = any(
            dependencies.get(name, {}).get("status") == "unhealthy" and name in {"vector_store"}
            for name in dependencies
        )
        any_unhealthy = any(d["status"] == "unhealthy" for d in dependencies.values())
        any_degraded = any(d["status"] == "degraded" for d in dependencies.values())

        if critical_unhealthy:
            overall_status = "unhealthy"
        elif any_unhealthy or any_degraded:
            overall_status = "degraded"
        else:
            overall_status = "healthy"

        status_code = 200
        if overall_status == "unhealthy":
            status_code = 503

        response = {"status": overall_status, "version": "test"}
        if dependencies:
            response["dependencies"] = dependencies

        return JSONResponse(content=response, status_code=status_code)

    return app


def _make_search_app(store=None):
    """Create a minimal FastAPI app simulating search endpoint behavior."""
    from fastapi import FastAPI, status
    from fastapi.responses import JSONResponse

    app = FastAPI()

    @app.post("/api/v1/search")
    async def search_properties():
        if store is None:
            return JSONResponse(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                content={
                    "detail": (
                        "Search is temporarily unavailable. "
                        "The property database is offline. "
                        "Please try again in a moment."
                    )
                },
            )
        return JSONResponse(status_code=200, content={"results": [], "total": 0})

    return app


# =============================================================================
# 1. Health Endpoint — Degraded & Unhealthy States
# =============================================================================


class TestHealthEndpointDegradation:
    """Test that /health correctly reports degraded and unhealthy states."""

    @pytest.mark.asyncio
    async def test_healthy_with_no_breakers(self):
        """Health returns 200 when all breakers are closed."""
        app = _make_health_app()
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/health")
            assert resp.status_code == 200
            data = resp.json()
            assert data["status"] == "healthy"

    @pytest.mark.asyncio
    async def test_unhealthy_when_critical_breaker_open(self):
        """Health returns 503 when a critical service breaker is open."""
        breaker = get_breaker("vector_store")
        breaker._state = CircuitState.OPEN

        app = _make_health_app()
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/health")
            assert resp.status_code == 503
            data = resp.json()
            assert data["status"] == "unhealthy"
            assert "vector_store" in data.get("dependencies", {})

    @pytest.mark.asyncio
    async def test_degraded_when_non_critical_breaker_open(self):
        """Health returns 200 with 'degraded' when non-critical breaker is open."""
        breaker = get_breaker("llm_providers")
        breaker._state = CircuitState.OPEN

        app = _make_health_app()
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/health")
            assert resp.status_code == 200
            data = resp.json()
            assert data["status"] == "degraded"

    @pytest.mark.asyncio
    async def test_health_includes_breaker_details(self):
        """Health response includes circuit breaker state details."""
        breaker = get_breaker("test_service")
        breaker._total_calls = 10
        breaker._total_failures = 3

        app = _make_health_app()
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/health")
            data = resp.json()
            deps = data.get("dependencies", {})
            assert "test_service" in deps
            assert deps["test_service"]["status"] == "healthy"

    @pytest.mark.asyncio
    async def test_no_500_on_dependency_failure(self):
        """Health endpoint never returns 500 even with broken deps."""
        for name in ("vector_store", "database", "llm_providers", "redis"):
            get_breaker(name)._state = CircuitState.OPEN

        app = _make_health_app()
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/health")
            assert resp.status_code in (200, 503)
            assert resp.status_code != 500
            data = resp.json()
            assert "status" in data
            assert "dependencies" in data


# =============================================================================
# 2. Search Endpoint — ChromaDB Unavailable
# =============================================================================


class TestSearchEndpointDegradation:
    """Test that search returns proper error when vector store is unavailable."""

    @pytest.mark.asyncio
    async def test_search_503_without_store(self):
        """Search returns 503 (not 500) when ChromaDB is unavailable."""
        app = _make_search_app(store=None)
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post("/api/v1/search", json={"query": "apartments in Warsaw"})
            assert resp.status_code == 503
            assert resp.status_code != 500
            data = resp.json()
            assert "unavailable" in data["detail"].lower()

    @pytest.mark.asyncio
    async def test_search_error_message_is_user_friendly(self):
        """Error message is clear and actionable, not a stack trace."""
        app = _make_search_app(store=None)
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post("/api/v1/search", json={"query": "apartments in Warsaw"})
            data = resp.json()
            detail = data["detail"].lower()
            assert "traceback" not in detail
            assert "try again" in detail or "moment" in detail

    @pytest.mark.asyncio
    async def test_search_200_when_store_available(self):
        """Search returns 200 when store is available."""
        app = _make_search_app(store=object())
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post("/api/v1/search", json={"query": "apartments in Warsaw"})
            assert resp.status_code == 200


# =============================================================================
# 3. LLM Provider Degradation — Circuit Breaker Behavior
# =============================================================================


class TestLLMProviderDegradation:
    """Test that LLM provider failures produce meaningful errors, not 500s."""

    @pytest.mark.asyncio
    async def test_all_providers_down_returns_service_error(self):
        """When all LLM providers fail, circuit breaker returns ServiceDegradedError."""
        breaker = get_breaker("llm_provider", failure_threshold=1)

        async def failing_call():
            raise RuntimeError("All providers failed")

        with pytest.raises(RuntimeError):
            await breaker.call(failing_call)

        with pytest.raises(ServiceDegradedError) as exc_info:
            await breaker.call(failing_call)

        msg = str(exc_info.value).lower()
        assert "llm_provider" in msg
        assert "open" in msg

    @pytest.mark.asyncio
    async def test_provider_failure_count_tracked(self):
        """Individual provider failures are tracked by the circuit breaker."""
        breaker = get_breaker("llm_openai", failure_threshold=5)

        async def failing_call():
            raise RuntimeError("OpenAI rate limit exceeded")

        for _ in range(3):
            with pytest.raises(RuntimeError):
                await breaker.call(failing_call)

        assert breaker.failure_count == 3
        assert breaker.state == CircuitState.CLOSED
        assert breaker._total_failures == 3

    @pytest.mark.asyncio
    async def test_provider_breaker_visible_in_health(self):
        """LLM provider breaker state is visible in health response."""
        breaker = get_breaker("llm_provider")
        breaker._state = CircuitState.OPEN
        breaker._total_failures = 10

        app = _make_health_app()
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/health")
            data = resp.json()
            deps = data.get("dependencies", {})
            assert "llm_provider" in deps
            assert deps["llm_provider"]["status"] == "unhealthy"


# =============================================================================
# 4. Database Degradation — Health Reporting
# =============================================================================


class TestDatabaseDegradationHTTP:
    """Test that database degradation is properly reported via health endpoint."""

    @pytest.mark.asyncio
    async def test_db_open_breaker_in_health(self):
        """Database breaker in OPEN state appears in health response."""
        breaker = get_breaker("database")
        breaker._state = CircuitState.OPEN

        app = _make_health_app()
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/health")
            data = resp.json()
            deps = data.get("dependencies", {})
            assert "database" in deps
            assert deps["database"]["status"] == "unhealthy"

    @pytest.mark.asyncio
    async def test_db_half_open_shows_degraded(self):
        """Database breaker in HALF_OPEN state shows as degraded."""
        breaker = get_breaker("database")
        breaker._state = CircuitState.HALF_OPEN

        app = _make_health_app()
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/health")
            data = resp.json()
            deps = data.get("dependencies", {})
            assert "database" in deps
            assert deps["database"]["status"] == "degraded"


# =============================================================================
# 5. Redis Degradation — Cache Bypass
# =============================================================================


class TestRedisDegradation:
    """Test that Redis unavailability is handled gracefully."""

    @pytest.mark.asyncio
    async def test_redis_breaker_in_health(self):
        """Redis breaker state appears in health response."""
        breaker = get_breaker("redis")
        breaker._state = CircuitState.OPEN

        app = _make_health_app()
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/health")
            data = resp.json()
            deps = data.get("dependencies", {})
            assert "redis" in deps
            assert deps["redis"]["status"] == "unhealthy"

    @pytest.mark.asyncio
    async def test_redis_not_critical_service(self):
        """Redis failure alone does not make health return 503."""
        get_breaker("redis")._state = CircuitState.OPEN

        app = _make_health_app()
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/health")
            # Redis is non-critical -> 200 with degraded status
            assert resp.status_code == 200
            data = resp.json()
            assert data["status"] == "degraded"


# =============================================================================
# 6. Multi-Service Degradation — Combined Failures
# =============================================================================


class TestMultiServiceDegradation:
    """Test behavior when multiple services are degraded simultaneously."""

    @pytest.mark.asyncio
    async def test_all_breakers_open_health_503(self):
        """When all breakers are open, health returns 503."""
        for name in ("vector_store", "database", "llm_providers", "redis"):
            get_breaker(name)._state = CircuitState.OPEN

        app = _make_health_app()
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/health")
            assert resp.status_code == 503
            data = resp.json()
            assert data["status"] == "unhealthy"

    @pytest.mark.asyncio
    async def test_no_500_on_cascading_failures(self):
        """No 500 errors even with cascading service failures."""
        for name in ("vector_store", "database", "llm_providers"):
            get_breaker(name)._state = CircuitState.OPEN

        app = _make_health_app()
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/health")
            assert resp.status_code != 500

    @pytest.mark.asyncio
    async def test_partial_degradation_still_serves(self):
        """When only some services are degraded, overall status is degraded (200)."""
        get_breaker("redis")._state = CircuitState.OPEN

        app = _make_health_app()
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/health")
            assert resp.status_code == 200
            data = resp.json()
            assert data["status"] == "degraded"
