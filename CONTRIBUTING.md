# Contributing to AI Real Estate Assistant

Thank you for your interest in contributing! This guide will help you get started.

## Quick Start

1. Fork the repository
2. Clone your fork: `git clone https://github.com/<your-username>/ai-real-estate-assistant.git`
3. Run setup: `make setup` (or `make install` for dependencies only)
4. Start developing: `make dev`

## Development Environment

### Prerequisites

- Python 3.12+
- Node.js 18+
- [uv](https://docs.astral.sh/uv/) (Python package manager)

### Backend Setup

```bash
cd apps/api
uv sync                    # Install Python dependencies
cp ../../.env.example ../../.env  # Configure environment
```

### Frontend Setup

```bash
cd apps/web
npm ci                     # Install Node dependencies
cp .env.example .env.local # Configure environment
```

## Code Style

### Python (Backend)

- **Formatter**: Ruff (line-length: 100, target: Python 3.12)
- **Type hints**: Required for all function signatures
- **Imports**: Use absolute imports from project root

```bash
cd apps/api && ruff check .     # Lint
cd apps/api && ruff format .    # Format
```

### TypeScript (Frontend)

- **Linter**: ESLint
- **Formatter**: Prettier (via lint-staged)

```bash
cd apps/web && npm run lint     # Lint
```

## Testing

### Backend

```bash
cd apps/api
pytest tests/unit tests/integration --cov=. -n auto  # All tests with coverage
pytest tests/unit/test_query_analyzer.py -v          # Single file
```

### Frontend

```bash
cd apps/web
npm test               # All tests
npm run test:ci        # CI with coverage
```

## Commit Convention

Format: `type(scope): description (Task #XX)`

| Type | Use for |
|------|---------|
| `feat` | New features |
| `fix` | Bug fixes |
| `docs` | Documentation |
| `refactor` | Code restructuring |
| `test` | Test additions/changes |
| `chore` | Maintenance, CI, tooling |
| `ci` | CI/CD changes |

## Pull Request Process

1. Create a feature branch from `dev`: `git checkout -b feature/short-description`
2. Make your changes with tests
3. Run `make lint` and `make test` to verify
4. Push and open a PR against `dev`
5. Ensure CI passes (linting, tests, security scans)

## Good First Issues

Looking for a place to start? Check these community-friendly issues:

- **[Community: Implement Telegram Bot MCP Connector](https://github.com/AleksNeStu/ai-real-estate-assistant/issues/16)** — Build a Telegram bot connector following the MCP pattern (Python async, HTTP APIs)

Filter by [`good first issue`](https://github.com/AleksNeStu/ai-real-estate-assistant/labels/good%20first%20issue) label for more opportunities.

## Architecture Overview

```
apps/
├── api/              # FastAPI backend (Python 3.12+)
│   ├── api/          # Routers, auth, middleware
│   ├── agents/       # HybridAgent, QueryAnalyzer
│   ├── mcp/          # MCP connector framework
│   ├── tools/        # LangChain tools
│   └── tests/        # Unit, integration, e2e tests
└── web/              # Next.js App Router frontend
    └── src/
        ├── app/      # Pages and API routes
        ├── components/ # UI components
        └── lib/      # API client, utilities
```

## Questions?

Open an issue with the `question` label and we will help you out.
