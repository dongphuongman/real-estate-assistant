# Security Review — MVP V4 (18.01.2026)

## Summary
- Backend hardened: CORS via env in prod; dev default API key blocked.
- Rate limiting active with per‑client RPM and request IDs.
- No secrets in frontend bundle; the web app injects `X-API-Key` server-side via the Next.js `/api/v1/*` proxy (`API_ACCESS_KEY`).

## Findings (Priority)
- Low: Frontend `npm audit` reports transitive issues (jest/ts-node/diff). Impact: dev‑only, low severity.
- Low: Streamlit V3 helpers still contain legacy patterns; isolated from V4 API.

## Actions Taken
- Added `ENVIRONMENT` and `CORS_ALLOW_ORIGINS` handling in [settings.py](file:///c:/Projects/ai-real-estate-assistant/config/settings.py).
- Enforced dev key block in prod in [api/auth.py](file:///c:/Projects/ai-real-estate-assistant/api/auth.py).
- Updated frontend docs to prohibit client secrets in production in [frontend/README.md](file:///c:/Projects/ai-real-estate-assistant/frontend/README.md).
- Fixed lint issues (unused import, bare except, print) in [common/cfg.py](file:///c:/Projects/ai-real-estate-assistant/common/cfg.py) and [utils.py](file:///c:/Projects/ai-real-estate-assistant/utils.py).

## Recommendations
- Frontend: add `overrides` to enforce `diff >= 8.0.3` if compatible; monitor jest chain.
- Backend: CI includes `pip-audit` job; pin critical dependencies; enable Trivy/Docker Scout for images.
- Backend: `pip-audit` temporarily ignores `GHSA-7gcm-g887-7qv7` / `CVE-2026-0994` (protobuf) because the current Google SDK dependency chain requires protobuf `<6`; remove the ignore once upstream provides a compatible fixed version.
- Logging: keep redaction policy; avoid sensitive payloads in logs.
- Input validation: continue using Pydantic; sanitize free‑text if used for search.
- Secrets: use platform secrets; never commit `.env`; rotate keys quarterly.

## API Key Rotation & Staged Revocation (CE)
- Use `API_ACCESS_KEYS` for safe key rotation (comma-separated). Any listed key is accepted.
- Keys are normalized: whitespace is trimmed, empty entries are ignored, and duplicates are removed.
- `X-API-Key` header values are also normalized (surrounding whitespace is accepted), but clients should send clean values.

Runbook (staged rotation, zero downtime):
1. Generate a new strong key (treat it like a password; do not log it).
2. Deploy with both keys valid:
   - `API_ACCESS_KEYS="NEW_KEY,OLD_KEY"`
3. Verify:
   - New key works (`GET /api/v1/verify-auth` with `X-API-Key: your-api-key
   - Old key still works during the transition window
4. Update clients/operators to use `NEW_KEY`.
5. Revoke the old key by redeploying with only the new key:
   - `API_ACCESS_KEYS="NEW_KEY"`
6. Confirm revocation:
   - Old key is rejected with 401/403

Notes:
- For Next.js deployments, keep secrets server-side: the `/api/v1/*` proxy injects `X-API-Key` from server env and does not allow `NEXT_PUBLIC_*` secret fallbacks.
- In `ENVIRONMENT=production`, `dev-secret-key` is treated as an invalid configuration; always set a unique key for production.

## Ongoing
- Add CI jobs: ruff, mypy, pytest, npm lint/test, bandit (static analysis), pip-audit.
- Evaluate move to pgvector on Neon/Supabase for managed persistence.
