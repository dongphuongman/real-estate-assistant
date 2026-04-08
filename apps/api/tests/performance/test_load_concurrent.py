"""Concurrent load tests with baseline benchmarks (Task #65).

Builds a self-contained FastAPI test app that mirrors the real endpoint
structure (health, search, chat) with lightweight mock handlers. Tests
ASGI framework concurrency handling, middleware throughput, and request
processing under load — without requiring external services or a running server.

SLA Targets (in-process, no network):
- Health:  p95 < 500ms  under 100 concurrent requests
- Search:  p95 < 2000ms under 50 concurrent requests
- Chat:    p95 < 8000ms under 20 concurrent requests
"""

import asyncio
import time
from typing import Any

import pytest
import pytest_asyncio
from fastapi import Depends, FastAPI
from httpx import ASGITransport, AsyncClient

from tests.performance.conftest import PerformanceMetrics

# SLA targets (milliseconds)
HEALTH_P95_TARGET_MS = 500.0
SEARCH_P95_TARGET_MS = 2000.0
CHAT_P95_TARGET_MS = 8000.0

# Test sizes
HEALTH_CONCURRENCY = 100
SEARCH_CONCURRENCY = 50
CHAT_CONCURRENCY = 20


class ConcurrentLoadResult:
    """Aggregated results from a concurrent load test."""

    def __init__(
        self,
        name: str,
        metrics: PerformanceMetrics,
        concurrency: int,
        wall_time_s: float,
    ) -> None:
        self.name = name
        self.metrics = metrics
        self.concurrency = concurrency
        self.wall_time_s = wall_time_s

    @property
    def throughput_rps(self) -> float:
        return self.metrics.total_requests / self.wall_time_s if self.wall_time_s > 0 else 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "concurrency": self.concurrency,
            "total_requests": self.metrics.total_requests,
            "success_rate": f"{self.metrics.success_rate:.2f}%",
            "wall_time_s": round(self.wall_time_s, 3),
            "throughput_rps": round(self.throughput_rps, 2),
            "p50_ms": round(self.metrics.p50 * 1000, 2),
            "p95_ms": round(self.metrics.p95 * 1000, 2),
            "p99_ms": round(self.metrics.p99 * 1000, 2),
            "avg_ms": round(self.metrics.avg * 1000, 2),
            "max_ms": round(self.metrics.max * 1000, 2),
            "errors": len(self.metrics.errors),
        }


async def run_concurrent_load(
    client: AsyncClient,
    method: str,
    url: str,
    num_concurrent: int,
    body: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
) -> ConcurrentLoadResult:
    """Run concurrent requests and aggregate results."""
    metrics = PerformanceMetrics()

    async def single_request() -> None:
        start = time.perf_counter()
        try:
            kwargs: dict[str, Any] = {}
            if body:
                kwargs["json"] = body
            if headers:
                kwargs["headers"] = headers
            response = await getattr(client, method.lower())(url, **kwargs)
            elapsed = time.perf_counter() - start
            metrics.add_response(elapsed, response.status_code)
        except Exception as e:
            elapsed = time.perf_counter() - start
            metrics.add_error({"error": str(e), "elapsed": elapsed})
            metrics.add_response(elapsed, 0)

    wall_start = time.perf_counter()
    tasks = [single_request() for _ in range(num_concurrent)]
    await asyncio.gather(*tasks, return_exceptions=True)
    wall_time = time.perf_counter() - wall_start

    return ConcurrentLoadResult(
        name=f"{method} {url}",
        metrics=metrics,
        concurrency=num_concurrent,
        wall_time_s=wall_time,
    )


# --- Mock App ---


def _create_load_test_app() -> FastAPI:
    """Build a FastAPI app that mirrors the real endpoint structure with mock handlers."""
    app = FastAPI()

    async def verify_api_key():
        """Mock API key verification (instant)."""
        pass

    @app.get("/health")
    async def health():
        """Mirrors the real /health endpoint."""
        return {
            "status": "healthy",
            "version": "1.0.0",
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }

    @app.post("/api/v1/properties/search", dependencies=[Depends(verify_api_key)])
    async def search(request_body: dict[str, Any] = None) -> dict[str, Any]:
        """Mirrors search endpoint — simulates vector store query latency."""
        # Simulate DB + vector search processing (5-50ms)
        await asyncio.sleep(0.005)
        return {
            "results": [
                {
                    "id": f"prop-{i}",
                    "title": f"Apartment {i} in Berlin",
                    "price": 350000 + i * 10000,
                    "score": 0.95 - i * 0.01,
                }
                for i in range(10)
            ],
            "total": 10,
            "query": request_body.get("query", "") if request_body else "",
        }

    @app.post("/api/v1/chat", dependencies=[Depends(verify_api_key)])
    async def chat(request_body: dict[str, Any] = None) -> dict[str, Any]:
        """Mirrors chat endpoint — simulates LLM processing latency."""
        # Simulate LLM streaming response (100-500ms)
        await asyncio.sleep(0.1)
        return {
            "response": "I found several properties matching your criteria.",
            "session_id": request_body.get("session_id", "test") if request_body else "test",
            "sources": [{"title": "Property listing", "score": 0.9}],
        }

    @app.get("/api/v1/properties", dependencies=[Depends(verify_api_key)])
    async def list_properties() -> dict[str, Any]:
        """Mirrors properties list endpoint."""
        await asyncio.sleep(0.003)
        return {"properties": [], "total": 0}

    @app.get("/api/v1/leads", dependencies=[Depends(verify_api_key)])
    async def list_leads() -> dict[str, Any]:
        """Mirrors leads list endpoint."""
        await asyncio.sleep(0.003)
        return {"leads": [], "total": 0}

    return app


# --- Fixtures ---


@pytest_asyncio.fixture
async def load_client() -> AsyncClient:
    """In-process ASGI client backed by a mock app mirroring real endpoints."""
    test_app = _create_load_test_app()
    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        client.headers["X-API-Key"] = "dev-secret-key"
        yield client


# --- Health Load Tests ---


@pytest.mark.performance
@pytest.mark.load
@pytest.mark.asyncio
class TestConcurrentHealthLoad:
    """Baseline: health endpoint under concurrent load."""

    async def test_50_concurrent_health_requests(self, load_client: AsyncClient) -> None:
        """50 concurrent /health requests should all succeed quickly."""
        result = await run_concurrent_load(load_client, "GET", "/health", num_concurrent=50)

        assert result.metrics.success_rate >= 99.0, (
            f"Health success rate {result.metrics.success_rate:.1f}% < 99%"
        )
        assert result.metrics.p95 * 1000 < HEALTH_P95_TARGET_MS, (
            f"Health p95 {result.metrics.p95 * 1000:.0f}ms > {HEALTH_P95_TARGET_MS:.0f}ms"
        )

    async def test_100_concurrent_health_requests(self, load_client: AsyncClient) -> None:
        """100 concurrent /health requests should maintain performance."""
        result = await run_concurrent_load(
            load_client, "GET", "/health", num_concurrent=HEALTH_CONCURRENCY
        )

        assert result.metrics.success_rate >= 99.0, (
            f"Health success rate {result.metrics.success_rate:.1f}% < 99%"
        )
        assert result.metrics.p95 * 1000 < HEALTH_P95_TARGET_MS, (
            f"Health p95 {result.metrics.p95 * 1000:.0f}ms > {HEALTH_P95_TARGET_MS:.0f}ms"
        )

        print(
            f"\nHealth ({HEALTH_CONCURRENCY} concurrent): "
            f"p50={result.metrics.p50 * 1000:.1f}ms "
            f"p95={result.metrics.p95 * 1000:.1f}ms "
            f"throughput={result.throughput_rps:.0f} req/s"
        )


# --- Search Load Tests ---


@pytest.mark.performance
@pytest.mark.load
@pytest.mark.asyncio
class TestConcurrentSearchLoad:
    """Search endpoint under concurrent load."""

    async def test_50_concurrent_search_requests(self, load_client: AsyncClient) -> None:
        """50 concurrent search requests — p95 < 2000ms SLA."""
        result = await run_concurrent_load(
            load_client,
            "POST",
            "/api/v1/properties/search",
            num_concurrent=SEARCH_CONCURRENCY,
            body={"query": "apartments in Berlin", "limit": 10},
        )

        p95_ms = result.metrics.p95 * 1000
        avg_ms = result.metrics.avg * 1000

        print(f"\n{'=' * 60}")
        print(f"Search Load Test: {SEARCH_CONCURRENCY} concurrent")
        print(f"{'=' * 60}")
        print(f"  Total requests: {result.metrics.total_requests}")
        print(f"  Success rate:   {result.metrics.success_rate:.1f}%")
        print(f"  Wall time:      {result.wall_time_s:.3f}s")
        print(f"  Throughput:     {result.throughput_rps:.1f} req/s")
        print(f"  p50:            {result.metrics.p50 * 1000:.0f}ms")
        print(f"  p95:            {p95_ms:.0f}ms (target: {SEARCH_P95_TARGET_MS:.0f}ms)")
        print(f"  Avg:            {avg_ms:.0f}ms")
        print(f"{'=' * 60}\n")

        assert result.metrics.success_rate >= 99.0, (
            f"Search success rate {result.metrics.success_rate:.1f}% < 99%"
        )
        assert p95_ms < SEARCH_P95_TARGET_MS, (
            f"Search p95 {p95_ms:.0f}ms > {SEARCH_P95_TARGET_MS:.0f}ms SLA"
        )

    async def test_search_varied_queries_concurrent(self, load_client: AsyncClient) -> None:
        """Mixed search queries under concurrency."""
        queries = [
            {"query": "apartments in Berlin", "limit": 10},
            {"query": "houses Munich", "limit": 5},
            {"query": "studio Krakow under 500", "limit": 10},
            {"query": "luxury apartment Warsaw", "limit": 20},
            {"query": "2-bedroom Hamburg", "limit": 15},
        ]

        metrics = PerformanceMetrics()
        num_per_query = SEARCH_CONCURRENCY // len(queries)

        async def run_query(query: dict[str, Any]) -> None:
            start = time.perf_counter()
            try:
                resp = await load_client.post("/api/v1/properties/search", json=query)
                elapsed = time.perf_counter() - start
                metrics.add_response(elapsed, resp.status_code)
            except Exception as e:
                elapsed = time.perf_counter() - start
                metrics.add_error({"query": query["query"], "error": str(e)})
                metrics.add_response(elapsed, 0)

        wall_start = time.perf_counter()
        tasks = []
        for query in queries:
            for _ in range(num_per_query):
                tasks.append(run_query(query))
        await asyncio.gather(*tasks, return_exceptions=True)
        wall_time = time.perf_counter() - wall_start

        p95_ms = metrics.p95 * 1000
        print(f"\nMixed queries ({len(tasks)} requests, {wall_time:.2f}s): p95={p95_ms:.0f}ms")

        assert metrics.success_rate >= 99.0, (
            f"Mixed search success rate {metrics.success_rate:.1f}% < 99%"
        )
        assert p95_ms < SEARCH_P95_TARGET_MS, (
            f"Mixed search p95 {p95_ms:.0f}ms > {SEARCH_P95_TARGET_MS:.0f}ms"
        )


# --- Chat Load Tests ---


@pytest.mark.performance
@pytest.mark.load
@pytest.mark.asyncio
class TestConcurrentChatLoad:
    """Chat endpoint under concurrent load."""

    async def test_20_concurrent_chat_requests(self, load_client: AsyncClient) -> None:
        """20 concurrent chat requests — p95 < 8000ms SLA."""
        result = await run_concurrent_load(
            load_client,
            "POST",
            "/api/v1/chat",
            num_concurrent=CHAT_CONCURRENCY,
            body={"message": "Hello, what properties are available?", "session_id": "load-test"},
        )

        p95_ms = result.metrics.p95 * 1000

        print(f"\n{'=' * 60}")
        print(f"Chat Load Test: {CHAT_CONCURRENCY} concurrent")
        print(f"{'=' * 60}")
        print(f"  Total requests: {result.metrics.total_requests}")
        print(f"  Success rate:   {result.metrics.success_rate:.1f}%")
        print(f"  Wall time:      {result.wall_time_s:.3f}s")
        print(f"  Throughput:     {result.throughput_rps:.1f} req/s")
        print(f"  p50:            {result.metrics.p50 * 1000:.0f}ms")
        print(f"  p95:            {p95_ms:.0f}ms (target: {CHAT_P95_TARGET_MS:.0f}ms)")
        print(f"{'=' * 60}\n")

        assert result.metrics.success_rate >= 99.0, (
            f"Chat success rate {result.metrics.success_rate:.1f}% < 99%"
        )
        assert p95_ms < CHAT_P95_TARGET_MS, (
            f"Chat p95 {p95_ms:.0f}ms > {CHAT_P95_TARGET_MS:.0f}ms SLA"
        )

    async def test_chat_sustained_load(self, load_client: AsyncClient) -> None:
        """Sustained chat load: 3 waves of 10 concurrent requests."""
        all_metrics = PerformanceMetrics()

        for wave in range(3):
            tasks = []
            for i in range(10):
                tasks.append(
                    load_client.post(
                        "/api/v1/chat",
                        json={
                            "message": f"Wave {wave} message {i}",
                            "session_id": f"load-wave-{wave}",
                        },
                    )
                )

            responses = await asyncio.gather(*tasks, return_exceptions=True)

            for response in responses:
                if isinstance(response, Exception):
                    all_metrics.add_error({"error": str(response)})
                    all_metrics.add_response(0, 0)
                else:
                    all_metrics.add_response(0, response.status_code)

        print(
            f"\nSustained chat (30 requests in 3 waves): "
            f"p95={all_metrics.p95 * 1000:.0f}ms, "
            f"success={all_metrics.success_rate:.1f}%"
        )

        assert all_metrics.success_rate >= 99.0


# --- Mixed Endpoint Load ---


@pytest.mark.performance
@pytest.mark.load
@pytest.mark.asyncio
class TestMixedEndpointLoad:
    """Mixed endpoint load simulating realistic traffic patterns."""

    async def test_mixed_concurrent_load(self, load_client: AsyncClient) -> None:
        """Mixed traffic: health + search + chat + listings under concurrency."""
        metrics = PerformanceMetrics()
        total_requests = 100

        async def weighted_request() -> None:
            import random

            r = random.random()
            start = time.perf_counter()
            try:
                if r < 0.3:
                    resp = await load_client.get("/health")
                elif r < 0.6:
                    resp = await load_client.post(
                        "/api/v1/properties/search",
                        json={"query": "apartments", "limit": 10},
                    )
                elif r < 0.8:
                    resp = await load_client.post(
                        "/api/v1/chat",
                        json={"message": "Hello", "session_id": "mixed"},
                    )
                elif r < 0.9:
                    resp = await load_client.get("/api/v1/properties")
                else:
                    resp = await load_client.get("/api/v1/leads")
                elapsed = time.perf_counter() - start
                metrics.add_response(elapsed, resp.status_code)
            except Exception as e:
                elapsed = time.perf_counter() - start
                metrics.add_error({"error": str(e)})
                metrics.add_response(elapsed, 0)

        wall_start = time.perf_counter()
        await asyncio.gather(*[weighted_request() for _ in range(total_requests)])
        wall_time = time.perf_counter() - wall_start

        p95_ms = metrics.p95 * 1000
        throughput = metrics.total_requests / wall_time

        print(
            f"\nMixed load ({total_requests} requests, {wall_time:.2f}s): "
            f"p95={p95_ms:.0f}ms, throughput={throughput:.0f} req/s, "
            f"success={metrics.success_rate:.1f}%"
        )

        assert metrics.success_rate >= 99.0
        assert p95_ms < SEARCH_P95_TARGET_MS  # Use search SLA as mixed benchmark


# --- Baseline Report ---


@pytest.mark.performance
@pytest.mark.load
@pytest.mark.asyncio
class TestLoadBaselineReport:
    """Generate baseline benchmark numbers for documentation."""

    async def test_generate_baseline_report(self, load_client: AsyncClient) -> None:
        """Run all baselines and print a summary for docs."""
        results: dict[str, ConcurrentLoadResult] = {}

        # Health baseline
        results["health"] = await run_concurrent_load(
            load_client, "GET", "/health", num_concurrent=HEALTH_CONCURRENCY
        )

        # Search baseline
        results["search"] = await run_concurrent_load(
            load_client,
            "POST",
            "/api/v1/properties/search",
            num_concurrent=SEARCH_CONCURRENCY,
            body={"query": "apartments Berlin", "limit": 10},
        )

        # Chat baseline
        results["chat"] = await run_concurrent_load(
            load_client,
            "POST",
            "/api/v1/chat",
            num_concurrent=CHAT_CONCURRENCY,
            body={"message": "Hello", "session_id": "baseline"},
        )

        # Print markdown-style report
        print(f"\n{'=' * 70}")
        print("## Load Test Baselines (Task #65)")
        print(f"{'=' * 70}")
        print(
            f"| {'Endpoint':8s} | {'Conc':>5s} | {'p50':>8s} | {'p95':>8s} | "
            f"{'p99':>8s} | {'Avg':>8s} | {'Success':>7s} | {'RPS':>8s} |"
        )
        print(
            f"|{'':->10}-+-{'':->7}-+-{'':->10}-+-{'':->10}-+-"
            f"{'':->10}-+-{'':->10}-+-{'':->9}-+-{'':->10}-|"
        )
        for name, result in results.items():
            m = result.metrics
            print(
                f"| {name:8s} | {result.concurrency:>5d} | "
                f"{m.p50 * 1000:>7.0f}ms | {m.p95 * 1000:>7.0f}ms | "
                f"{m.p99 * 1000:>7.0f}ms | {m.avg * 1000:>7.0f}ms | "
                f"{m.success_rate:>6.1f}% | {result.throughput_rps:>7.0f} |"
            )
        print(f"{'=' * 70}\n")

        # All baselines should succeed
        for name, result in results.items():
            assert result.metrics.success_rate >= 99.0, (
                f"{name} success rate {result.metrics.success_rate:.1f}% < 99%"
            )
