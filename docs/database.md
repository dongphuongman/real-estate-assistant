# AI Real Estate Assistant — Database

> Reference pattern: [02.003 §2](../../../../docs/research/architecture/02.003-large-saas-auth-database-pattern-2026-06-16.md)
> [ADR-015](../../../../docs/architecture/decisions/015-database-standards.md),
> [ADR-025](../../../../docs/architecture/decisions/025-postgres-version-pinning.md)

| Item | Value |
|---|---|
| Engine | PostgreSQL 16 LTS (prod) / 18 (dev) |
| ORM | SQLAlchemy + Alembic |
| Connection env var | `DATABASE_URL` |

## Multi-tenancy

Single-tenant demo deployment (per-tenant scoping deferred to post-freeze).

## Migration workflow

```bash
cd apps/api
alembic revision --autogenerate -m "<change>"
alembic upgrade head
```

## Schema overview

- `users` — auth + profile
- `conversations` — chat session metadata
- `messages` — conversation history
- `property_cache` — recent property search results (TTL cleanup)
- `mls_listings` — ingested MLS data
