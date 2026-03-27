# SPRAV Remaining Tasks Prompt

## Context
Frontend tests are fixed and passing (40/40 suites, 410 tests). Coverage thresholds are met (53.5% statements).
This prompt covers the remaining validation tasks for full SPRAV compliance.

## Remaining Tasks

### 1. Backend Unit Tests
```bash
cd apps/api
python -m pytest tests/unit --cov=. --cov-report=term -n auto
```
**Target:** All tests pass, coverage >= 90% on critical paths

### 2. Backend Integration Tests
```bash
cd apps/api
python -m pytest tests/integration --cov=. --cov-report=term
```
**Target:** All tests pass, coverage >= 70%

### 3. Security Scans
```bash
# All security scans
python scripts/security/local_scan.py

# Individual scans:
python scripts/security/local_scan.py --scan-only=secrets   # Gitleaks
python scripts/security/local_scan.py --scan-only=semgrep   # Semgrep
python scripts/security/local_scan.py --scan-only=bandit    # Bandit
python scripts/security/local_scan.py --scan-only=pip-audit # Dependencies
```
**Target:** 0 secrets, 0 high-confidence vulnerabilities

### 4. Linting & Type Checking
```bash
# Backend
cd apps/api
ruff check .
mypy .

# Frontend
cd apps/web
npm run lint
```
**Target:** No errors (warnings acceptable)

### 5. Docker Build & Smoke Test
```bash
# Build containers
docker compose -f deploy/compose/docker-compose.yml build

# Run smoke test
python scripts/docker/compose_smoke.py --timeout-seconds 600
```
**Target:** Build succeeds, health checks pass

### 6. Full CI Pipeline (Local)
```bash
make ci
```
**Target:** All jobs pass

---

## Execution Order

1. **Backend Tests** (parallel):
   - Unit tests
   - Integration tests

2. **Security Scans** (parallel with tests):
   - Gitleaks
   - Semgrep
   - Bandit
   - pip-audit

3. **Linting** (parallel):
   - Backend: ruff + mypy
   - Frontend: ESLint

4. **Docker** (sequential, after tests pass):
   - Build images
   - Run smoke test

5. **Final Report**:
   - Compile results
   - Go/No-Go recommendation

---

## SPRAV Report Template

```markdown
# SPRAV Report: [Version]

**Date:** [YYYY-MM-DD]
**Status:** [GO / NO-GO / CONDITIONAL]

## Results Summary

| Category | Status | Pass | Fail | Notes |
|----------|--------|------|------|-------|
| Backend Unit | [✓/✗] | N | N | |
| Backend Integration | [✓/✗] | N | N | |
| Frontend Tests | ✅ | 410 | 0 | Already passing |
| Security Scans | [✓/✗] | N | N | |
| Linting | [✓/✗] | N | N | |
| Docker Smoke | [✓/✗] | N | N | |

## Defects

| ID | Severity | Component | Description | Status |
|----|----------|-----------|-------------|--------|
| | | | | |

## Recommendation

[GO / NO-GO with conditions]
```

---

## Commands to Run (Copy-Paste)

```bash
# From project root: e:\nestlab-repo\nest-solo\products\large\ai-real-estate-assistant

# 1. Backend tests
cd apps/api && python -m pytest tests/unit tests/integration --cov=. --cov-report=term -n auto

# 2. Security
cd ../.. && python scripts/security/local_scan.py

# 3. Linting
cd apps/api && ruff check . && mypy .
cd ../web && npm run lint

# 4. Docker
cd ../.. && docker compose -f deploy/compose/docker-compose.yml up --build -d
python scripts/docker/compose_smoke.py

# 5. Full CI
make ci
```
