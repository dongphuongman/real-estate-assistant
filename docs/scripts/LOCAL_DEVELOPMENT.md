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

Extra flags:
- `--dry-run`: prints the commands and key env defaults (secrets redacted) without starting anything
- `--service backend|frontend|all`: start only the backend or only the frontend (default: `all`)
- `--docker-mode auto|cpu|gpu|ask`: choose Docker runtime mode (default: `auto`)
- `--internet`: enable web research and start the `internet` Docker profile (SearxNG)
- `--no-bootstrap`: skip `uv` environment bootstrap in local backend mode (assumes deps already installed)

### Windows (PowerShell)

```powershell
.\scripts\core\local\run.ps1
```

Force a specific mode:

```powershell
python .\scripts\launcher\start.py --mode docker --docker-mode cpu
python .\scripts\launcher\start.py --mode docker --docker-mode gpu
python .\scripts\launcher\start.py --mode docker --docker-mode gpu --internet
python .\scripts\launcher\start.py --mode local
python .\scripts\launcher\start.py --mode local --service backend
python .\scripts\launcher\start.py --mode local --dry-run
```

Convenience commands:

```powershell
.\scripts\core\docker\cpu.ps1
.\scripts\core\docker\gpu.ps1
.\scripts\core\docker\gpu-internet.ps1
```

### Linux

```sh
chmod +x ./scripts/core/linux/*.sh
./scripts/core/linux/start.sh --mode local
```

Force a specific mode:

```sh
./scripts/core/linux/start.sh --mode docker
./scripts/core/linux/docker.sh gpu
```

## Python environment setup (uv)

This creates `.venv/` and installs project dependencies (plus dev extras):

### Windows

```powershell
.\scripts\core\env\setup.ps1
```

### Linux

```sh
./scripts/core/env/setup.sh
```

## Local ports and env defaults

- Backend: http://localhost:8001
- Frontend: http://localhost:3001

Local mode defaults:

- `ENVIRONMENT=development`
- `API_ACCESS_KEY=dev-secret-key`
- `NEXT_PUBLIC_API_URL=/api/v1`
- `BACKEND_API_URL=http://localhost:8001/api/v1`

For real provider usage, set `OPENAI_API_KEY` / `ANTHROPIC_API_KEY` / `GOOGLE_API_KEY` in your shell env (or `.env` used by Docker Compose).
