# AGENTS.md - AI Real Estate Assistant

> AI Agent instructions for real estate conversational AI platform

## Build & Run

```bash
# Root monorepo (both frontend and backend)
npm run dev

# Backend only
npm run dev:api
cd apps/api && python -m uvicorn api.main:app --reload --port 8000

# Frontend only
npm run dev:web
cd apps/web && npm run dev

# Docker
docker compose -f deploy/compose/docker-compose.yml up --build
```

## Test

```bash
# All tests
npm run test

# Backend tests only
npm run test:api
python -m pytest tests/unit                    # Unit tests
python -m pytest tests/integration             # Integration tests

# Frontend tests only
npm run test:web

# E2E tests
npm run test:e2e
```

## Code Style

- **Python**: Ruff formatter, line-length 100, targets Python 3.11+
- **TypeScript**: ESLint with Next.js config
- **Git**: Pre-commit hooks with Gitleaks, Semgrep, lint-staged

## Architecture

- **Backend**: FastAPI with hybrid agent (RAG + tool-based)
- **Frontend**: Next.js App Router with React 19
- **Vector Store**: ChromaDB for semantic search
- **LLM Support**: OpenAI, Anthropic, Google, Grok, DeepSeek, Ollama

## Key Rules

- Frontend uses API proxy pattern for secure key injection
- Backend uses HybridPropertyAgent for query routing
- QueryAnalyzer classifies intent and complexity

## Constraints

- Never expose API keys in browser
- Never use GPL/AGPL packages as dependencies (the project itself is MIT-licensed)
- Always use environment variables for secrets

## LLM Providers

Configure via environment variables:
- `OPENAI_API_KEY` - GPT-4o, GPT-4o-mini
- `ANTHROPIC_API_KEY` - Claude 3.5
- `GOOGLE_API_KEY` - Gemini
- `XAI_API_KEY` - Grok 2
- `DEEPSEEK_API_KEY` - DeepSeek
- `OLLAMA_BASE_URL` - Local models

## 🚨 CRITICAL RULE: UNIFIED LOCAL-DEV SCRIPTS 🚨
**DO NOT use standard commands like 
pm run dev or docker-compose up directly.**
This project belongs to the NestSolo meta-repo and uses dynamic port allocation to prevent cross-agent conflicts.

To run the project locally, you MUST use the provided wrapper scripts:
- Native: ./scripts/start.sh or .\scripts\start.ps1
- Docker: ./scripts/start-docker.sh or .\scripts\start-docker.ps1
- Stop: ./scripts/stop.sh or .\scripts\stop.ps1

**How to find the active port:**
Once the script starts, the assigned port is written to the runtime directory. To discover it, read:
cat .runtime/port.txt
Alternatively, use cat .runtime/ports.json for a full list of allocated service ports.

Never commit .runtime/ files or modify the shell wrapper scripts directly (they are meta-repo templates). Project-specific configuration lives exclusively in scripts/env.sh and scripts/env.ps1.
