# Project Structure Refactoring PRD

## Overview
Restructure the ai-real-estate-assistant project to improve organization by separating concerns:
- Development scripts
- CI/CD scripts
- Docker/deployment files
- Security scanning scripts

## Current State Issues
1. `scripts/` directory mixes different types of scripts (dev, ci, docs, security, validation)
2. `security-scan.py` is in root instead of scripts/
3. `.devcontainer/devcontainer.json` is outdated (references old Streamlit app.py)
4. Docker files scattered in root (Dockerfile.backend, docker-compose.yml)
5. No clear separation between local dev and CI/CD scripts

## Proposed Structure

```
project/
├── .devcontainer/          # Dev container configuration
│   └── devcontainer.json   # Updated for FastAPI + Next.js
├── .github/
│   └── workflows/          # CI/CD workflows
│       ├── ci.yml
│       └── semgrep.yml
├── deploy/                 # NEW: Docker and deployment files
│   ├── docker/
│   │   ├── Dockerfile.backend
│   │   └── Dockerfile.frontend
│   ├── compose/
│   │   ├── docker-compose.yml
│   │   └── docker-compose.gpu.yml
│   └── k8s/                # Future: Kubernetes manifests
├── scripts/
│   ├── ci/                 # CI/CD parity scripts
│   │   ├── ci_parity.py
│   │   ├── ci_full.py
│   │   ├── compose_smoke.py
│   │   ├── coverage_gate.py
│   │   └── security.py     # RENAMED: security_local.py
│   ├── dev/                # Local development scripts
│   │   ├── bootstrap_uv.py
│   │   ├── start.py
│   │   ├── start.sh
│   │   ├── start.ps1
│   │   ├── setup.sh
│   │   ├── setup.ps1
│   │   ├── run-ci-full.ps1
│   │   ├── run-pre-commit.ps1
│   │   ├── run-docker-cpu.ps1
│   │   ├── run-docker-gpu.ps1
│   │   ├── run-docker-gpu-internet.ps1
│   │   ├── verify_ollama.ps1
│   │   └── sync_claude_mcp_from_trae.ps1
│   ├── docs/               # Documentation generation
│   │   ├── export_openapi.py
│   │   ├── generate_api_reference.py
│   │   └── update_api_reference_full.py
│   ├── security/           # Security scanning utilities
│   │   ├── forbidden_tokens_check.py
│   │   └── security_scan.py
│   └── validation/         # Validation scripts
│       ├── system_validate.py
│       └── validate_taskmaster.py
├── Makefile                # NEW: Quick commands
└── security-scan.py        # REMOVED: Use scripts/ci/security.py instead
```

## Tasks

### 1. Update .devcontainer Configuration
- Update devcontainer.json for FastAPI + Next.js stack
- Remove Streamlit references
- Add proper extensions and ports
- Update setup commands for uv and modern Python

### 2. Create deploy/ Directory
- Move `Dockerfile.backend` to `deploy/docker/Dockerfile.backend`
- Move `frontend/Dockerfile.frontend` to `deploy/docker/Dockerfile.frontend`
- Move `docker-compose.yml` to `deploy/compose/docker-compose.yml`
- Create GPU compose variant
- Update all path references in Docker files

### 3. Rename security_local.py
- Rename `scripts/ci/security_local.py` to `scripts/ci/security.py`
- Update documentation references
- Remove root `security-scan.py` wrapper

### 4. Update CI/CD Paths
- Update `.github/workflows/ci.yml` with new paths
- Update docker-compose references to `deploy/compose/`

### 5. Create Makefile
Create convenient targets:
- `make security` - Run security scans
- `make test` - Run all tests
- `make lint` - Run linting
- `make docker-up` - Start docker compose
- `make ci` - Run full CI locally

### 6. Update Documentation
- Update README.md with new structure
- Update CLAUDE.md with new script paths
- Update all references to moved files

## Success Criteria
1. All scripts have clear, single-purpose locations
2. Docker/deployment files isolated in deploy/
3. Dev container configuration updated and working
4. Makefile provides quick access to common commands
5. All CI/CD paths updated
6. Documentation reflects new structure
