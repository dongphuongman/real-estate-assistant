# ADR 0010: API Versioning Strategy

## Status

Accepted

## Context

The API uses `/api/v1/` prefix for all endpoints but has no mechanism to prevent breaking changes within v1. The CI pipeline runs OpenAPI drift checks but does not detect breaking changes such as removed fields or changed types.

PRD NFR Scalability requires "versioned endpoints." Without breaking-change detection, a backward-incompatible change can reach production undetected.

## Decision

We adopt **URI-path versioning** (`/api/v1/`, `/api/v2/`) with the following enforcement mechanisms:

### 1. API Version Header

All API responses include `X-API-Version: <major>.<minor>.<patch>` via the `APIVersioningMiddleware`. This allows clients to detect which version they are communicating with.

### 2. Breaking-Change Detection in CI

The CI pipeline includes an OpenAPI schema diff step that:
- Exports the current OpenAPI schema from the running app
- Compares it against a committed baseline (`docs/api-v1-baseline.json`)
- Fails the build if breaking changes are detected:
  - Removed endpoints
  - Removed required request fields
  - Removed response fields
  - Changed field types
  - Changed required/optional status

Non-breaking changes (adding endpoints, adding optional fields) are allowed.

### 3. Baseline Schema Management

- `docs/api-v1-baseline.json` is the committed OpenAPI schema baseline for v1
- To intentionally introduce a breaking change, update the baseline and increment the major version
- Minor/patch versions reflect additive changes only

### 4. Version Bump Rules

| Change Type | Version Impact | Example |
|-------------|---------------|---------|
| Add endpoint | Minor | New `/api/v1/reports` endpoint |
| Add optional field | Minor | New `phone` field in response |
| Remove endpoint | Major (new prefix) | `/api/v2/search` replaces v1 |
| Remove field | Major | Dropping `legacy_id` from response |
| Change field type | Major | `price: str` to `price: float` |

## Consequences

**Positive:**
- CI catches accidental breaking changes before merge
- Clients can verify API version via response header
- Clear documentation of versioning rules
- Baseline schema serves as living API contract

**Negative:**
- CI step adds ~30 seconds to pipeline
- Baseline schema file must be updated for intentional breaking changes
- Multiple API versions may need to coexist during migration

## Implementation

- `apps/api/api/middleware/versioning.py` — `X-API-Version` header middleware
- `.github/workflows/ci.yml` — OpenAPI diff step
- `docs/api-v1-baseline.json` — Committed schema baseline
- `apps/api/tests/integration/test_versioning.py` — Contract tests
