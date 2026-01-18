# ADR-0002: Authentication — API Key (MVP) → Accounts (Paid)

## Context
MVP uses a single API key to protect `/api/v1/*`. Frontend currently supports `NEXT_PUBLIC_API_KEY` for local dev.

## Decision
- MVP: keep API key header `X-API-Key` for backend access; never expose in production builds.
- Future paid: user accounts (email/OAuth), server-side sessions, per-user quotas/roles.

## Consequences
- Simple free-tier protection with rate limiting.
- Migration path to proper auth without breaking API surface.

