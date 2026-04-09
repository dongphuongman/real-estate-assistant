"""Chat endpoint p95 performance benchmark tests (Task #51).

Measures p95 latency for various chat query patterns:
- Simple factual queries (greeting, basic questions)
- Medium hybrid queries (with property context)
- Complex agent+tools queries (web search, multi-step reasoning)
- Streaming vs non-streaming response comparison

SLA Target: p95 < 8s for chat endpoints (includes LLM processing).
"""

import statistics
from typing import Any

import pytest
from httpx import AsyncClient

# Test configuration
WARMUP_REQUESTS = 2  # Fewer warmups for chat (LLM latency)
BENCHMARK_REQUESTS = 20  # Fewer requests for chat (expensive)
P95_TARGET_MS = 8000.0  # 8 seconds (LLM processing is slower)
P99_TARGET_MS = 15000.0  # 15 seconds (allowable spike)
AVG_TARGET_MS = 5000.0  # 5 seconds average
SIMPLE_AVG_TARGET_MS = 3000.0  # 3 seconds for simple queries


class ChatBenchmarkStats:
    """Calculate benchmark statistics from raw measurements."""

    def __init__(self, measurements: list[float]) -> None:
        self.measurements = sorted(measurements)
        self.count = len(measurements)

    @property
    def min_ms(self) -> float:
        return self.measurements[0] * 1000 if self.measurements else 0.0

    @property
    def max_ms(self) -> float:
        return self.measurements[-1] * 1000 if self.measurements else 0.0

    @property
    def avg_ms(self) -> float:
        return statistics.mean(self.measurements) * 1000 if self.measurements else 0.0

    @property
    def median_ms(self) -> float:
        return statistics.median(self.measurements) * 1000 if self.measurements else 0.0

    @property
    def p95_ms(self) -> float:
        if not self.measurements:
            return 0.0
        index = int(self.count * 0.95)
        return self.measurements[min(index, self.count - 1)] * 1000

    @property
    def p99_ms(self) -> float:
        if not self.measurements:
            return 0.0
        index = int(self.count * 0.99)
        return self.measurements[min(index, self.count - 1)] * 1000

    @property
    def std_dev_ms(self) -> float:
        if len(self.measurements) < 2:
            return 0.0
        return statistics.stdev(self.measurements) * 1000

    def to_dict(self) -> dict[str, Any]:
        return {
            "count": self.count,
            "min_ms": round(self.min_ms, 2),
            "max_ms": round(self.max_ms, 2),
            "avg_ms": round(self.avg_ms, 2),
            "median_ms": round(self.median_ms, 2),
            "p95_ms": round(self.p95_ms, 2),
            "p99_ms": round(self.p99_ms, 2),
            "std_dev_ms": round(self.std_dev_ms, 2),
        }


@pytest.mark.benchmark
@pytest.mark.asyncio
class TestSimpleChatBenchmark:
    """Benchmark tests for simple chat queries (greetings, basic questions)."""

    async def test_greeting_p95(
        self,
        authed_perf_client: AsyncClient,
    ) -> None:
        """Simple greeting should have p95 < 8s, avg < 3s."""
        measurements: list[float] = []
        query = {"message": "Hello", "stream": False}

        # Warmup
        for _ in range(WARMUP_REQUESTS):
            await authed_perf_client.post("/api/v1/chat", json=query)

        # Benchmark
        for _ in range(BENCHMARK_REQUESTS):
            import time

            start = time.perf_counter()
            response = await authed_perf_client.post("/api/v1/chat", json=query)
            elapsed = time.perf_counter() - start
            measurements.append(elapsed)
            assert response.status_code == 200

        stats = ChatBenchmarkStats(measurements)

        # Assertions
        assert stats.p95_ms < P95_TARGET_MS, (
            f"Greeting p95 ({stats.p95_ms:.0f}ms) exceeds target ({P95_TARGET_MS:.0f}ms)\n"
            f"Stats: {stats.to_dict()}"
        )
        assert stats.avg_ms < SIMPLE_AVG_TARGET_MS, (
            f"Greeting avg ({stats.avg_ms:.0f}ms) exceeds simple target ({SIMPLE_AVG_TARGET_MS:.0f}ms)"
        )

    async def test_basic_question_p95(
        self,
        authed_perf_client: AsyncClient,
    ) -> None:
        """Basic factual question should have p95 < 8s."""
        measurements: list[float] = []
        query = {"message": "What services do you offer?", "stream": False}

        # Warmup
        for _ in range(WARMUP_REQUESTS):
            await authed_perf_client.post("/api/v1/chat", json=query)

        # Benchmark
        for _ in range(BENCHMARK_REQUESTS):
            import time

            start = time.perf_counter()
            response = await authed_perf_client.post("/api/v1/chat", json=query)
            elapsed = time.perf_counter() - start
            measurements.append(elapsed)
            assert response.status_code == 200

        stats = ChatBenchmarkStats(measurements)

        assert stats.p95_ms < P95_TARGET_MS, (
            f"Basic question p95 ({stats.p95_ms:.0f}ms) exceeds target ({P95_TARGET_MS:.0f}ms)"
        )
        assert stats.avg_ms < AVG_TARGET_MS, (
            f"Basic question avg ({stats.avg_ms:.0f}ms) exceeds target ({AVG_TARGET_MS:.0f}ms)"
        )


@pytest.mark.benchmark
@pytest.mark.asyncio
class TestMediumHybridChatBenchmark:
    """Benchmark tests for medium complexity hybrid queries (with property context)."""

    async def test_property_search_question_p95(
        self,
        authed_perf_client: AsyncClient,
    ) -> None:
        """Property search question should have p95 < 8s."""
        measurements: list[float] = []
        query = {
            "message": "What apartments are available in Berlin?",
            "stream": False,
        }

        # Warmup
        for _ in range(WARMUP_REQUESTS):
            await authed_perf_client.post("/api/v1/chat", json=query)

        # Benchmark
        for _ in range(BENCHMARK_REQUESTS):
            import time

            start = time.perf_counter()
            response = await authed_perf_client.post("/api/v1/chat", json=query)
            elapsed = time.perf_counter() - start
            measurements.append(elapsed)
            assert response.status_code == 200

        stats = ChatBenchmarkStats(measurements)

        assert stats.p95_ms < P95_TARGET_MS, (
            f"Property search p95 ({stats.p95_ms:.0f}ms) exceeds target ({P95_TARGET_MS:.0f}ms)\n"
            f"Stats: {stats.to_dict()}"
        )

    async def test_filtered_property_question_p95(
        self,
        authed_perf_client: AsyncClient,
    ) -> None:
        """Filtered property question should have p95 < 8s."""
        measurements: list[float] = []
        query = {
            "message": "Show me 2-bedroom apartments under 500k in Munich",
            "stream": False,
        }

        # Warmup
        for _ in range(WARMUP_REQUESTS):
            await authed_perf_client.post("/api/v1/chat", json=query)

        # Benchmark
        for _ in range(BENCHMARK_REQUESTS):
            import time

            start = time.perf_counter()
            response = await authed_perf_client.post("/api/v1/chat", json=query)
            elapsed = time.perf_counter() - start
            measurements.append(elapsed)
            assert response.status_code == 200

        stats = ChatBenchmarkStats(measurements)

        assert stats.p95_ms < P95_TARGET_MS, (
            f"Filtered property p95 ({stats.p95_ms:.0f}ms) exceeds target ({P95_TARGET_MS:.0f}ms)"
        )

    async def test_comparison_question_p95(
        self,
        authed_perf_client: AsyncClient,
    ) -> None:
        """Comparison question should have p95 < 8s."""
        measurements: list[float] = []
        query = {
            "message": "Compare apartments in Berlin vs Munich",
            "stream": False,
        }

        # Warmup
        for _ in range(WARMUP_REQUESTS):
            await authed_perf_client.post("/api/v1/chat", json=query)

        # Benchmark
        for _ in range(BENCHMARK_REQUESTS):
            import time

            start = time.perf_counter()
            response = await authed_perf_client.post("/api/v1/chat", json=query)
            elapsed = time.perf_counter() - start
            measurements.append(elapsed)
            assert response.status_code == 200

        stats = ChatBenchmarkStats(measurements)

        assert stats.p95_ms < P95_TARGET_MS, (
            f"Comparison p95 ({stats.p95_ms:.0f}ms) exceeds target ({P95_TARGET_MS:.0f}ms)"
        )


@pytest.mark.benchmark
@pytest.mark.asyncio
class TestComplexAgentBenchmark:
    """Benchmark tests for complex agent+tools queries (web search, multi-step)."""

    async def test_complex_analysis_p95(
        self,
        authed_perf_client: AsyncClient,
    ) -> None:
        """Complex analysis should have p95 < 8s."""
        measurements: list[float] = []
        query = {
            "message": "Analyze the property market trends in Germany and recommend the best cities for investment",
            "stream": False,
        }

        # Warmup
        for _ in range(WARMUP_REQUESTS):
            await authed_perf_client.post("/api/v1/chat", json=query)

        # Benchmark
        for _ in range(BENCHMARK_REQUESTS):
            import time

            start = time.perf_counter()
            response = await authed_perf_client.post("/api/v1/chat", json=query)
            elapsed = time.perf_counter() - start
            measurements.append(elapsed)
            assert response.status_code == 200

        stats = ChatBenchmarkStats(measurements)

        assert stats.p95_ms < P95_TARGET_MS, (
            f"Complex analysis p95 ({stats.p95_ms:.0f}ms) exceeds target ({P95_TARGET_MS:.0f}ms)\n"
            f"Stats: {stats.to_dict()}"
        )

    async def test_multi_step_reasoning_p95(
        self,
        authed_perf_client: AsyncClient,
    ) -> None:
        """Multi-step reasoning query should have p95 < 8s."""
        measurements: list[float] = []
        query = {
            "message": "I have 300k budget. What's the best apartment I can get in Berlin, Munich, or Hamburg? Compare price per square meter.",
            "stream": False,
        }

        # Warmup
        for _ in range(WARMUP_REQUESTS):
            await authed_perf_client.post("/api/v1/chat", json=query)

        # Benchmark
        for _ in range(BENCHMARK_REQUESTS):
            import time

            start = time.perf_counter()
            response = await authed_perf_client.post("/api/v1/chat", json=query)
            elapsed = time.perf_counter() - start
            measurements.append(elapsed)
            assert response.status_code == 200

        stats = ChatBenchmarkStats(measurements)

        assert stats.p95_ms < P95_TARGET_MS, (
            f"Multi-step p95 ({stats.p95_ms:.0f}ms) exceeds target ({P95_TARGET_MS:.0f}ms)"
        )


@pytest.mark.benchmark
@pytest.mark.asyncio
class TestStreamingBenchmark:
    """Benchmark tests for streaming vs non-streaming chat."""

    async def test_streaming_vs_non_streaming_p95(
        self,
        authed_perf_client: AsyncClient,
    ) -> None:
        """Compare streaming vs non-streaming performance."""
        query = {"message": "What apartments are available in Berlin?"}

        # Non-streaming measurements
        non_streaming: list[float] = []
        for _ in range(BENCHMARK_REQUESTS):
            import time

            start = time.perf_counter()
            response = await authed_perf_client.post(
                "/api/v1/chat", json={**query, "stream": False}
            )
            elapsed = time.perf_counter() - start
            non_streaming.append(elapsed)
            assert response.status_code == 200

        # Streaming measurements
        streaming: list[float] = []
        for _ in range(BENCHMARK_REQUESTS):
            import time

            start = time.perf_counter()
            response = await authed_perf_client.post("/api/v1/chat", json={**query, "stream": True})
            # Consume the full stream
            content = b""
            async for chunk in response.aiter_bytes():
                content += chunk
                if b"data: [DONE]" in content:
                    break
            elapsed = time.perf_counter() - start
            streaming.append(elapsed)

        non_streaming_stats = ChatBenchmarkStats(non_streaming)
        streaming_stats = ChatBenchmarkStats(streaming)

        # Both should meet p95 target
        assert non_streaming_stats.p95_ms < P95_TARGET_MS, (
            f"Non-streaming p95 ({non_streaming_stats.p95_ms:.0f}ms) exceeds target"
        )
        assert streaming_stats.p95_ms < P95_TARGET_MS, (
            f"Streaming p95 ({streaming_stats.p95_ms:.0f}ms) exceeds target"
        )

        # Print comparison
        print(f"\n{'=' * 60}")
        print("Streaming vs Non-Streaming Comparison")
        print(f"{'=' * 60}")
        print(f"{'Metric':<15} | {'Non-Streaming':<15} | {'Streaming':<15}")
        print(f"{'-' * 60}")
        print(
            f"{'Avg (ms)':<15} | {non_streaming_stats.avg_ms:<15.0f} | {streaming_stats.avg_ms:<15.0f}"
        )
        print(
            f"{'P95 (ms)':<15} | {non_streaming_stats.p95_ms:<15.0f} | {streaming_stats.p95_ms:<15.0f}"
        )
        print(
            f"{'P99 (ms)':<15} | {non_streaming_stats.p99_ms:<15.0f} | {streaming_stats.p99_ms:<15.0f}"
        )
        print(f"{'=' * 60}\n")

    async def test_streaming_first_chunk_latency(
        self,
        authed_perf_client: AsyncClient,
    ) -> None:
        """Measure time to first chunk for streaming (TTFT)."""
        measurements: list[float] = []
        query = {"message": "Hello", "stream": True}

        for _ in range(BENCHMARK_REQUESTS):
            import time

            start = time.perf_counter()
            response = await authed_perf_client.post("/api/v1/chat", json=query)

            # Measure time to first chunk
            first_chunk_time = None
            async for chunk in response.aiter_bytes():
                if first_chunk_time is None and chunk:
                    first_chunk_time = time.perf_counter() - start
                    break

            # Consume rest of stream
            async for chunk in response.aiter_bytes():
                if b"data: [DONE]" in chunk:
                    break

            if first_chunk_time is not None:
                measurements.append(first_chunk_time)

        stats = ChatBenchmarkStats(measurements)

        # First chunk should be fast (time to first token)
        assert stats.p95_ms < 2000.0, f"TTFT p95 ({stats.p95_ms:.0f}ms) exceeds 2s target"

        print("\nTime to First Token (TTFT):")
        print(f"  Avg: {stats.avg_ms:.0f}ms")
        print(f"  P95: {stats.p95_ms:.0f}ms")
        print(f"  P99: {stats.p99_ms:.0f}ms\n")


@pytest.mark.benchmark
@pytest.mark.asyncio
class TestChatBenchmarkSummary:
    """Generate summary benchmark report for chat endpoints."""

    async def test_generate_chat_benchmark_report(
        self,
        authed_perf_client: AsyncClient,
    ) -> None:
        """Generate a comprehensive benchmark report for chat endpoints."""
        report: dict[str, Any] = {
            "target_p95_ms": P95_TARGET_MS,
            "target_avg_ms": AVG_TARGET_MS,
            "queries": {},
        }

        test_queries = [
            ("greeting", {"message": "Hello", "stream": False}),
            (
                "property_search",
                {"message": "What apartments are available in Berlin?", "stream": False},
            ),
            ("filtered", {"message": "2-bedroom apartments under 500k", "stream": False}),
            (
                "complex",
                {"message": "Compare property markets in Berlin vs Munich", "stream": False},
            ),
        ]

        for name, query in test_queries:
            measurements: list[float] = []

            # Warmup
            for _ in range(WARMUP_REQUESTS):
                await authed_perf_client.post("/api/v1/chat", json=query)

            # Benchmark
            for _ in range(BENCHMARK_REQUESTS):
                import time

                start = time.perf_counter()
                response = await authed_perf_client.post("/api/v1/chat", json=query)
                elapsed = time.perf_counter() - start
                measurements.append(elapsed)
                assert response.status_code == 200

            stats = ChatBenchmarkStats(measurements)
            report["queries"][name] = stats.to_dict()
            report["queries"][name]["passes_p95"] = stats.p95_ms < P95_TARGET_MS
            report["queries"][name]["passes_avg"] = stats.avg_ms < AVG_TARGET_MS

        # Overall summary
        all_pass_p95 = all(q["passes_p95"] for q in report["queries"].values())
        all_pass_avg = all(q["passes_avg"] for q in report["queries"].values())
        report["summary"] = {
            "all_queries_pass_p95": all_pass_p95,
            "all_queries_pass_avg": all_pass_avg,
        }

        # Print report for visibility
        print(f"\n{'=' * 60}")
        print("Chat Benchmark Report")
        print(f"{'=' * 60}")
        print(f"Target p95: {P95_TARGET_MS:.0f}ms")
        print(f"Target avg: {AVG_TARGET_MS:.0f}ms")
        print(f"{'-' * 60}")
        for name, stats in report["queries"].items():
            status = "PASS" if stats["passes_p95"] else "FAIL"
            print(
                f"{name:20s} | p95: {stats['p95_ms']:6.0f}ms | avg: {stats['avg_ms']:6.0f}ms | {status}"
            )
        print(f"{'=' * 60}\n")

        assert all_pass_p95, "Some chat queries did not meet p95 target"
