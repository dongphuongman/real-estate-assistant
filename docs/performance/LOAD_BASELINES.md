# Load Test Baselines (Task #65)

Baseline numbers from concurrent load tests using in-process ASGI transport.
These numbers represent the app's throughput without network overhead.

## Test Environment

- **Platform:** CI (ubuntu-latest) / Local dev
- **Transport:** ASGI (in-process, no network)
- **Runner:** pytest-asyncio with asyncio.gather

## SLA Targets

| Endpoint | Concurrency | p95 Target | Avg Target |
|----------|-------------|------------|------------|
| Health   | 50          | < 500ms    | < 100ms    |
| Search   | 50          | < 2000ms   | < 1000ms   |
| Chat     | 20          | < 8000ms   | < 5000ms   |

## Baseline Results

> Numbers below are representative. Run `make load-test` for current values.

### Health (`GET /health`)

| Metric | Value |
|--------|-------|
| Concurrency | 50 |
| p50 | ~5ms |
| p95 | ~20ms |
| p99 | ~50ms |
| Avg | ~10ms |
| Throughput | ~5000 req/s |
| Success rate | 100% |

### Search (`POST /api/v1/properties/search`)

| Metric | Value |
|--------|-------|
| Concurrency | 50 |
| p50 | ~100ms |
| p95 | ~500ms |
| p99 | ~1000ms |
| Avg | ~200ms |
| Throughput | ~250 req/s |
| Success rate | >95% |

### Chat (`POST /api/v1/chat`)

| Metric | Value |
|--------|-------|
| Concurrency | 20 |
| p50 | ~1000ms |
| p95 | ~3000ms |
| p99 | ~5000ms |
| Avg | ~1500ms |
| Throughput | ~15 req/s |
| Success rate | >90% |

## Running Load Tests

```bash
# All load tests (concurrent + existing)
make load-test

# Search-specific p95 benchmarks
make benchmark-search

# Chat-specific p95 benchmarks
make benchmark-chat

# Full load tests (requires running server)
RUN_LOAD_TESTS=1 pytest tests/performance/test_load.py -v
```

## Notes

- Baselines were established on 2026-04-08
- Chat latency depends heavily on LLM provider response time
- Search latency is dominated by vector store query + reranking
- In-process baselines exclude network latency (~5-50ms per request)
