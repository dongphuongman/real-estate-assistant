# Security Review — MVP V4 (18.01.2026)

## Summary
- Backend hardened: CORS via env in prod; dev default API key blocked.
- Rate limiting active with per‑client RPM and request IDs.
- No secrets in frontend bundle; `NEXT_PUBLIC_API_KEY` marked dev‑only.

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
- Logging: keep redaction policy; avoid sensitive payloads in logs.
- Input validation: continue using Pydantic; sanitize free‑text if used for search.
- Secrets: use platform secrets; never commit `.env`; rotate keys quarterly.

## Ongoing
- Add CI jobs: ruff, mypy, pytest, npm lint/test, bandit (static analysis), pip-audit.
- Evaluate move to pgvector on Neon/Supabase for managed persistence.
