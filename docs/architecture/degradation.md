# Graceful Degradation

This document describes the graceful degradation behavior when external
dependencies (LLM providers, ChromaDB, Redis, database) are unavailable.

## Circuit Breaker Pattern

All external service calls are protected by circuit breakers
(`core/circuit_breaker.py`). Each service has its own breaker with:

| Parameter | Default | Purpose |
|-----------|---------|---------|
| `failure_threshold` | 5 | Consecutive failures before opening |
| `recovery_timeout` | 60s | Time before half-open probe |
| `success_threshold` | 3 | Consecutive successes to close |
| `call_timeout` | 30s | Per-call timeout |

### State Machine

```
CLOSED ────(failure_threshold reached)──→ OPEN
   ↑                                       │
   │                                       │ (recovery_timeout)
   │                                       ↓
   └──(success_threshold reached)─── HALF_OPEN
                                       │
                                       │ (any failure)
                                       ↓
                                     OPEN
```

- **CLOSED**: Normal operation. Calls pass through.
- **OPEN**: Failing fast. Calls raise `ServiceDegradedError` immediately.
- **HALF_OPEN**: Probing. Limited calls pass through to test recovery.

## Degradation Scenarios

### ChromaDB Unavailable

- **Search endpoint** (`POST /api/v1/search`): Returns `503 Service Unavailable`
  with message "Search is temporarily unavailable. The property database is
  offline. Please try again in a moment."
- **Chat endpoint** (`POST /api/v1/chat`): Returns `503 Service Unavailable`
  with similar message.
- **Circuit breaker**: `vector_store` breaker opens after 5 consecutive failures.

### All LLM Providers Down

- The `llm_provider` circuit breaker opens after repeated provider failures.
- Subsequent calls raise `ServiceDegradedError` with provider name and state.
- Error message is user-friendly ("Please retry later"), not a stack trace.
- **HTTP status**: 503 (not 500).

### Single LLM Provider Fails

- Individual provider failures are tracked by provider-specific breakers.
- The routing system falls back to the next available provider (Gemini → OpenAI
  → Anthropic → Ollama).
- If all fail, the global `llm_provider` breaker opens.

### Redis Down

- **Cache bypass**: If Redis is unavailable, requests proceed without caching.
- Responses are served from the data source directly.
- **Health endpoint**: Redis breaker state visible, marked as unhealthy.
- **No 500 errors**: Redis failure is non-critical.

### Database Down

- **Health endpoint**: Reports `unhealthy` status with database breaker state.
- **HTTP status**: 503 when critical database operations fail.
- **Circuit breaker**: `database` breaker opens after 5 consecutive failures.

## Health Endpoint

`GET /health?include_dependencies=true` returns:

| Scenario | HTTP Status | `status` Field |
|----------|-------------|----------------|
| All healthy | 200 | `healthy` |
| Non-critical failure (Redis, single LLM) | 200 | `degraded` |
| Critical failure (ChromaDB, DB) | 503 | `unhealthy` |

### Response Structure

```json
{
  "status": "degraded",
  "version": "4.x.x",
  "timestamp": "2026-04-11T12:00:00Z",
  "uptime_seconds": 3600.0,
  "dependencies": {
    "vector_store": {
      "status": "healthy",
      "message": "OK (1500 items indexed)",
      "latency_ms": 2.5
    },
    "llm_provider": {
      "status": "unhealthy",
      "message": "State: open, failures: 5/10"
    }
  }
}
```

## Testing

Run resilience tests:

```bash
make test-resilience
```

Or directly:

```bash
cd apps/api
pytest tests/resilience/ -v
```

Integration tests for circuit breaker internals:

```bash
cd apps/api
pytest tests/integration/test_graceful_degradation.py -v
```
