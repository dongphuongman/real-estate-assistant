# AI Real Estate Assistant — Authentication

> Reference pattern: [02.003 §1](../../../../docs/research/architecture/02.003-large-saas-auth-database-pattern-2026-06-16.md)
> Per [ADR-019](../../../../docs/architecture/decisions/019-product-portfolio-isolation.md).

**FastAPI JWT (stateless Bearer tokens)** per the standard Large-SaaS pattern.
- `python-jose[cryptography]` + `passlib[bcrypt]` (rounds=12, 72-byte truncation).
- FastAPI `Depends(get_current_user)` in `apps/api/auth.py`.
- Conversation session tokens (longer-lived than access tokens) for chat continuity.

## Env vars

See [docs/env.md](env.md): `SECRET_KEY`, `ALGORITHM`, `ACCESS_TOKEN_EXPIRE_MINUTES`.
