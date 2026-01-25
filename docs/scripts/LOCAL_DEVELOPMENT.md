# Local Development (Windows + Linux)

## Prerequisites

- Python 3.11+
- Node.js + npm
- uv (Python package manager)
- Docker + Docker Compose (optional, recommended)

## Install uv (no pip)

### Windows

```powershell
winget install Astral.UV
```

### Linux

```sh
curl -LsSf https://astral.sh/uv/install.sh | sh
```

## Start the app

The helper script supports two modes:

- `docker`: runs `docker compose up --build` (recommended)
- `local`: runs backend (uvicorn) + frontend (next dev) on your machine

If you run with `--mode auto` (default), it uses Docker if available, otherwise falls back to local mode.

### Windows (PowerShell)

```powershell
.\scripts\dev\start.ps1
```

Force a specific mode:

```powershell
.\scripts\dev\start.ps1 --mode docker
.\scripts\dev\start.ps1 --mode local
```

### Linux

```sh
chmod +x ./scripts/dev/*.sh
./scripts/dev/start.sh
```

Force a specific mode:

```sh
./scripts/dev/start.sh --mode docker
./scripts/dev/start.sh --mode local
```

## Python environment setup (uv)

This creates `.venv/` and installs project dependencies (plus dev extras):

### Windows

```powershell
.\scripts\dev\setup.ps1
```

### Linux

```sh
./scripts/dev/setup.sh
```

## Local ports and env defaults

- Backend: http://localhost:8000
- Frontend: http://localhost:3000

Local mode defaults:

- `ENVIRONMENT=development`
- `API_ACCESS_KEY=dev-secret-key`
- `NEXT_PUBLIC_API_URL=/api/v1`
- `BACKEND_API_URL=http://localhost:8000/api/v1`

For real provider usage, set `OPENAI_API_KEY` / `ANTHROPIC_API_KEY` / `GOOGLE_API_KEY` in your shell env (or `.env` used by Docker Compose).
