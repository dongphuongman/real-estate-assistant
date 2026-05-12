# Security Full Cleanup + Deployment Pipeline Configuration

**Date:** 2026-05-12
**Status:** Approved
**Scope:** Security vulnerability fixes, Dependabot automation, deploy pipeline setup, branch protection, CodeQL triage

## Context

The CI pipeline is green after recent fixes, but the GitHub Security tab shows 83 Dependabot alerts and 100 CodeQL alerts (36 open). No deployment environment is configured — secrets are missing, environments don't exist, and the deploy workflow (`deploy.yml`) has never run successfully. Dependabot security updates are disabled. The project needs a comprehensive security cleanup and deployment pipeline configuration before it can ship to production.

## Section 1: Security Cleanup

### 1.1 Dependabot Alerts (83 open)

**Action:** Enable Dependabot security updates via GitHub API.

**Action:** Update `.github/dependabot.yml` to add:
- `allow: security updates only` for pip/npm ecosystems
- Group major version updates to reduce PR noise
- Auto-label security PRs with `security` label

**Action:** Update high-severity packages:
- `urllib3` — CVE-2026-44432 (decompression bomb bypass)
- `langchain-core` — unsafe deserialization
- `lodash` — code injection via template
- `pyasn1` — DoS via unbounded recursion
- `protobuf` — JSON recursion depth bypass

### 1.2 CodeQL Alerts (100 open)

| Category | Count | Severity | Action |
|----------|-------|----------|--------|
| `py/partial-ssrf` | 1 | critical | Fix code |
| `py/log-injection` | 61 | medium | Fix code |
| `py/weak-sensitive-data-hashing` | 3 | high | Fix code |
| `py/ineffectual-statement` | 14 | note | Fix dead code |
| `py/unused-global-variable` | 11 | note | Bulk dismiss |
| `py/unused-local-variable` | 8 | note | Bulk dismiss |
| `py/unused-import` | 2 | note | Bulk dismiss |

### 1.3 Code Fixes Required

**SSRF fix** — `apps/api/data/adapters/air_quality_adapter.py`:
- Add URL allowlist for known air quality API domains
- Validate resolved IP is not private/internal
- Reject redirects to non-HTTPS URLs

**Log injection fix** — 8 files with `py/log-injection`:
- `apps/api/data/adapters/transport_adapter.py`
- `apps/api/api/routers/settings.py`
- `apps/api/data/adapters/registry.py`
- Other files with user-controlled data passed to `logger.*()`
- Sanitize by stripping newline/carriage-return characters from logged data

**Weak hashing fix** — 3 files with `py/weak-sensitive-data-hashing`:
- Replace SHA1/MD5 with SHA256 for sensitive data hashing
- Use `hashlib.sha256()` or `hashlib.pbkdf2_hmac()` depending on context

**Dead code cleanup** — files with `py/ineffectual-statement`:
- `apps/api/agents/services/valuation.py`
- `apps/api/agents/services/legal_check.py`
- `apps/api/agents/services/data_enrichment.py`
- `apps/api/agents/services/crm_connector.py`
- `apps/api/services/esignature_service.py`

### 1.4 CodeQL Configuration

Create `.github/codeql/codeql-config.yml`:
- Ignore paths: tests, venv, .history, migrations, node_modules
- Query suite: `security-extended` (drop `security-and-quality` to reduce note-level noise)
- Add `packs` for custom dismiss rules if available

Bulk-dismiss all 21 `note`-severity alerts via `gh api` after config is in place.

## Section 2: Deployment Pipeline

### 2.1 Target Architecture

Both staging and production use **Render** (backend) + **Vercel** (frontend).

| Environment | Backend | Frontend | Branch |
|-------------|---------|----------|--------|
| Staging | Render staging service | Vercel preview | `dev` |
| Production | Render production service | Vercel production | `main` |

### 2.2 Deploy Workflow Changes (`deploy.yml`)

Current: triggers only on `main` push.

New triggers:

| Branch | Trigger | Target Environment |
|--------|---------|-------------------|
| `dev` | Auto (push) | staging |
| `main` | Auto (push) | production |
| Any | Manual (`workflow_dispatch`) | User-selected (staging/production) |

Key changes:
- Add `dev` branch to `on.push.branches`
- Use environment variable to select Render/Vercel target based on branch
- Staging deploys use preview/ephemeral URLs
- Production deploys require environment approval

### 2.3 GitHub Environments

Create via GitHub API:

**`staging`:**
- No required reviewers
- Auto-rollback on failure
- Secrets: `RENDER_SERVICE_ID_API_STAGING`, `RENDER_BACKEND_URL_STAGING`

**`production`:**
- Required reviewer: `@AleksNeStu`
- Auto-rollback on failure
- Secrets: `RENDER_SERVICE_ID_API`, `RENDER_BACKEND_URL`, `VERCEL_TOKEN`

### 2.4 GitHub Secrets Required

User must configure these in GitHub repo Settings > Secrets:

| Secret | Purpose | Required For |
|--------|---------|-------------|
| `RENDER_API_KEY` | Render API authentication | All deploys |
| `RENDER_SERVICE_ID_API` | Production backend service | Production |
| `RENDER_SERVICE_ID_API_STAGING` | Staging backend service | Staging |
| `RENDER_BACKEND_URL` | Production backend URL | Smoke tests |
| `RENDER_BACKEND_URL_STAGING` | Staging backend URL | Smoke tests |
| `VERCEL_TOKEN` | Vercel deployment | Frontend deploys |
| `API_ACCESS_KEY` | Smoke test auth | Post-deploy |

### 2.5 Smoke Tests (existing, keep)

The existing smoke test job in `deploy.yml` covers:
- Backend health check (`/health`)
- API authentication (`/api/v1/properties?limit=1`)
- Frontend 200 OK

No changes needed to smoke tests.

## Section 3: Branch Protection

### 3.1 `main` Branch Rules

- Require pull request before merging (1 approval required)
- Require status checks: `backend-lint`, `backend-tests (unit)`, `frontend-build`, `gitleaks`
- Require branches to be up to date
- Do not allow force pushes
- Do not allow deletions

### 3.2 `dev` Branch Rules

- Require status checks: `backend-lint`, `backend-tests (unit)`, `frontend-build`
- Allow direct pushes (no PR required for dev)
- Do not allow force pushes
- Do not allow deletions

### 3.3 Custom Branch Deploys

Custom/feature branches cannot auto-deploy. They can only trigger manual deploys via `workflow_dispatch` to staging environment.

## Section 4: Execution Plan

5 parallel workstreams:

1. **Security code fixes** — SSRF, log injection, weak hashing, dead code (files listed in 1.3)
2. **Dependabot configuration** — Enable security updates, update `dependabot.yml`
3. **Deploy pipeline** — Update `deploy.yml`, create environments, configure secrets docs
4. **Branch protection** — Configure via `gh api` for `main` and `dev`
5. **CodeQL triage** — Create config file, bulk-dismiss note alerts

## Verification

1. Run `make ci` locally — all checks pass
2. Push to `dev` — CI passes, staging deploy triggers
3. Check GitHub Security tab — Dependabot alerts dropping, CodeQL alerts < 10
4. Verify `dev` auto-deploys to staging Render+Vercel
5. Create PR `dev` → `main`, merge — production deploy triggers
6. Verify production URLs respond with healthy status
