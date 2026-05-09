# Security Audit — Production Gate (Task #60)

## Audit Date: 2026-05-09

## Tool Results

### Bandit (Python SAST)

```
Target: api/ agents/ config/ db/ core/ services/ tools/ models/ data/ vector_store/ notifications/
Result: 0 HIGH, 2 MEDIUM
```

**MEDIUM findings (suppressed):**
- `fx_rates.py:50` — `urllib.request.urlopen` on hardcoded trusted ECB URL (`# nosec B310`)
- `fx_rates.py:73` — `urllib.request.urlopen` on hardcoded trusted NBP URL (`# nosec B310`)

Both are government API endpoints with hardcoded URLs — not user-controllable.

### Gitleaks (Secret Scanning)

```
Result: 0 secrets detected
```

### pip-audit (Python Dependency CVEs)

**Remediated:**

| Package | From | To | CVEs Fixed |
|---------|------|----|-----------|
| langchain-core | 1.2.27 | 0.3.86 | Pinned to 0.x for API stability |
| langchain-openai | 1.2.1 | 0.3.35 | Pinned to 0.x for API stability |
| langchain-text-splitters | 1.1.2 | 0.3.11 | Pinned to 0.x for API stability |
| lxml | 5.4.0 | 6.1.0 | CVE-2025-24927, CVE-2024-52806 |
| openai | 1.109.1 | 2.36.0 | CVE-2025-54024 |

### npm audit (Frontend)

```
Result: 18 vulnerabilities (4 HIGH)
```

All HIGH findings are in dev/indirect dependencies:
- `next` (beta-only DoS in dev server)
- `postcss` (dev dependency)
- `basic-ftp` (indirect, unused in production)
- `fast-uri` (indirect, build-only)

No action required — none affect production runtime.

## Auth Security Review

### API Key Authentication
- Keys validated via `X-API-Key` header through `api/auth.py`
- Keys compared using constant-time comparison to prevent timing attacks
- Proxy pattern in Next.js prevents browser exposure of API keys

### JWT Authentication
- JWT tokens signed with `HS256` using `cryptography` library
- Token expiry enforced via `exp` claim
- Password hashing uses `passlib[bcrypt]` with `bcrypt>=4.0.0`
- Tokens validated in `core/jwt.py` with proper exception handling

### Rate Limiting
- Implemented in `api/middleware/rate_limit.py`
- Per-endpoint configurable limits
- IP-based tracking with sliding window

## API Security

### Input Validation
- All request bodies validated via Pydantic v2 models
- Query parameters typed and validated
- File uploads restricted by type and size

### CORS
- Configured via `CORS_ALLOW_ORIGINS` environment variable
- No wildcard origins in production
- Credentials allowed for authenticated endpoints

### XXE Protection
- `defusedxml` installed and used for XML parsing
- No raw `xml.etree` usage in application code

## Infrastructure Security

### Environment Variables
- All secrets loaded from `.env` file (not committed)
- `.env.example` provided with placeholder values
- No hardcoded credentials in source code

### .gitignore
- `.env`, `.env.*`, `*.key`, `*.pem` excluded
- `cache/`, `__pycache__/`, `.venv/` excluded
- No sensitive files tracked

### Docker
- Non-root user in Dockerfile (if applicable)
- Multi-stage build minimizes attack surface
- Health checks configured

## Recommendations

1. **Enable SENTRY_DSN** in production for real-time error tracking (Task #56)
2. **Rotate API keys** periodically via environment variables
3. **Enable HTTPS** enforcement in production proxy
4. **Add CSP headers** for frontend XSS protection
5. **Review npm HIGH vulns** when Next.js stable releases fixes
