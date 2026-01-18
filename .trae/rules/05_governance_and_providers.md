# Governance & Providers (Trae Rules)

## Deployment
- **Env**: Secrets in env vars (never commit). Use `.env.example`.
- **Build**: Docker preferred. CI runs lint/test/security.
- **Release**: SemVer. Tag images. Maintainer approval for `prod`.
- **Rollback**: Revert to previous tag. Use feature flags.

## Governance
- **Enforcement**: CI gates, CODEOWNERS, Log redaction.
- **Change Control**: Updates via PR. Quarterly review.

## AI Providers
- **Supported**: OpenAI, Anthropic, Google, Grok, DeepSeek, Ollama.
- **New Providers**: Require RFC, implementation in `models/providers/`, tests, and docs.
- **Compliance**: No PII to external providers without approval.
