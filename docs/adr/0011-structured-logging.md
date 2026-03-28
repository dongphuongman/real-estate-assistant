# ADR 0011: Structured Logging Standard

## Status

Accepted

## Context

PRD NFR Observability requires "structured logs, traces, metrics, request IDs, audit events." The backend has a JSON logging formatter but lacks a documented log level policy, The frontend uses raw `console.*` calls with no structure. Log entries must be parseable by log aggregation tools (e.g. Datadog, Loki).

## Decision

### 1. Structured JSON Format (Backend)

All backend log output uses the `JsonFormatter` in `utils/json_logging.py`. Required fields:

| Field | Type | Description |
|-------|------|-------------|
| `ts` | int (epoch ms) | Timestamp |
| `level` | string | Log level (DEBUG, INFO, WARNING, ERROR) |
| `service` | string | Service identifier (`ai-real-estate-api`) |
| `logger` | string | Python logger name |
| `message` | string | Human-readable message |

Optional fields (via `extra` in logger calls):

| Field | Type | When |
|-------|------|------|
| `request_id` | string | Set by observability middleware |
| `event` | string | Domain event name (e.g. `search.completed`) |
| `client_id` | string | Authenticated user ID |
| `method` | string | HTTP method |
| `path` | string | Request path |
| `status` | int | HTTP status code |
| `duration_ms` | float | Operation duration |
| `exception` | string | Exception traceback (auto) |

### 2. Structured JSON Format (Frontend)

Frontend uses `logger.ts` in `apps/web/src/lib/logger.ts`. Same required fields as backend, with `service: ai-real-estate-web`.

### 3. Log Level Policy

| Level | When to Use | Examples |
|-------|-------------|---------|
| **DEBUG** | Detailed diagnostic info, only in dev | Query plans, internal state, cache hits/misses |
| **INFO** | Normal operational events | Request received, search completed, cache initialized |
| **WARNING** | Unexpected but recoverable situations | Rate limit hit, fallback provider used, config missing |
| **ERROR** | Failures requiring attention | Uncaught exceptions, service unavailable, data corruption |

**Rules:**
- DEBUG logs are suppressed in production (frontend only; backend via LOG_LEVEL env var)
- Never log sensitive data: passwords, API keys, tokens, secrets, authorization headers, cookies
- Always include `request_id` when available (set by observability middleware)
- Use `extra` dict for structured fields, not string interpolation in message
- Exception info is auto-attached by formatter when using `logger.exception()`

### 4. Sensitive Data Prevention

The `JsonFormatter.check_sensitive_data()` method scans log messages for patterns: `password`, `api_key`, `secret`, `token`, `authorization`, `cookie`. An automated test validates that no log output contains these patterns.

## Consequences

**Positive:**
- Logs parseable by aggregation tools (Loki, Datadog)
- Consistent format across backend and frontend
- Request ID correlation for distributed tracing
- Automated sensitive data detection
- Clear policy reduces ambiguity

**Negative:**
- JSON overhead (slight performance cost vs plain text)
- All developers must follow the structured format
- Frontend debug logs hidden in production

## Implementation

- `apps/api/utils/json_logging.py` — Backend JSON formatter with `service` field
- `apps/web/src/lib/logger.ts` — Frontend structured logger
- `apps/api/tests/unit/test_structured_logging.py` — Existing tests
- `apps/api/tests/unit/test_sensitive_log_scan.py` — Sensitive data scan test (new)
