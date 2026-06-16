# AI Real Estate Assistant — Environment Variables

> Reference: [ADR-027](../../../../docs/architecture/decisions/027-hardware-key-secrets-governance.md),
> [ADR-005](../../../../docs/architecture/decisions/005-secret-management-policy.md).

## Required

| Variable | Notes |
|---|---|
| `DATABASE_URL` | PostgreSQL connection <!-- pragma: allowlist secret --> |
| `SECRET_KEY` | JWT signing — `openssl rand -hex 32` |
| `ALGORITHM` | JWT algorithm (HS256 default) |
| `OPENAI_API_KEY` | Conversational AI (OpenAI) |
| `NEXT_PUBLIC_APP_URL` | Frontend base URL |

## Optional

| Variable | Enables |
|---|---|
| `GOOGLE_API_KEY` | Gemini fallback for AI |
| `RESEND_API_KEY` | Transactional email |
| `MLS_API_KEY` | MLS data integration |

## Getting secrets

- DB URL: KeePass → `DB/AI-RealEstate/PROD`.
- AI provider keys: per [ADR-004](../../../../docs/architecture/decisions/004-ai-provider-governance.md).
