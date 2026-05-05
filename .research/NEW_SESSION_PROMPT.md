# AI Real Estate Assistant - Deployment Session Prompt

**Created:** 2026-05-05
**Branch:** dev
**Goal:** Clean up PRs, merge relevant ones, fix CI/CD, and deploy to production

---

## 🎯 Primary Objective

Deploy AI Real Estate Assistant to production:
- **Backend → Render.com** (https://realestate-api.onrender.com)
- **Frontend → Vercel** (https://ai-real-estate-assistant.vercel.app)

---

## 📋 Current Repository State

### Branch: `dev`
- Up to date with origin/dev
- Latest commit: `e08dccd` - "fix(lint): fix import order..."
- Working directory: Clean (no uncommitted changes)

### Repository Structure (IMPORTANT)
```
AleksNeStu/ai-real-estate-assistant  ← PRIMARY (work here)
├── DevScaver/ai-real-estate-assistant  ← Mirror (sync via parent)
└── NestLab-Tech/ai-real-estate-assistant  ← Mirror (sync via parent)
```

**DO NOT push to mirrors** - they sync automatically from primary.

---

## 🔴 Pull Requests Status

### ✅ MERGED (Give credit to authors)
- **PR #32** by @KrabbiAI - Security fixes (JWT CVSS 9.1 + XXE CVSS 7.5)
  - Status: MERGED
  - Thank you comment posted: https://github.com/AleksNeStu/ai-real-estate-assistant/pull/32#issuecomment-4375705243

- **PR #37** by @Jwrede - Tokentoll LLM cost analysis
  - Status: MERGED
  - Thank you comment posted: https://github.com/AleksNeStu/ai-real-estate-assistant/pull/37#issuecomment-4375706251

### 🔶 NEW OPEN PRs (Need Review - 11 PRs)
All from @dependabot - need to check relevance:

| PR # | Title | Type | Action Needed |
|------|-------|------|---------------|
| **#38** | chore(deps-web): bump eslint-config-next 16.2.1→16.2.4 | Frontend | Check relevance |
| **#39** | chore(deps-api): update redis 5.0.0→8.0.0 | Backend | Check breaking changes |
| **#40** | chore(deps-api): update zstandard 0.23.0→0.25.0 | Backend | Check relevance |
| **#41** | chore(deps-web): bump @lhci/cli 0.14.0→0.15.1 | Frontend | Check relevance |
| **#42** | chore(deps-api): update langchain-chroma 0.2.0→1.1.0 | Backend | **MAJOR** - check compatibility |
| **#43** | chore(deps-api): update tiktoken 0.5.0→0.12.0 | Backend | **MAJOR** - check breaking |
| **#44** | chore(deps-api): update python-multipart 0.0.22→0.0.27 | Backend | Check relevance |
| **#45** | chore(deps-web): bump eslint-config-next 16.2.1→16.2.4 | Frontend | Duplicate of #38? |
| **#46** | chore(deps-web): bump next-intl 4.9.1→4.11.0 | Frontend | Check relevance |
| **#47** | chore(deps-web): bump tailwindcss 4.2.1→4.2.4 | Frontend | Check relevance |
| **#48** | chore(deps-web): bump jest-resolve 30.2.0→30.3.0 | Frontend | Check relevance |

### ✅ CLOSED (Already handled)
- PRs #17-36: Dependabot dependencies (most changes already applied locally)
- PR #25: jest update (skipped due to lockfile conflicts)

---

## 🚨 CI/CD Issues (FIXED)

### Previous Failures:
- `frontend` job: Lint warnings only (0 errors)
- `backend` job: Import order issues
- `secret-validation` job: Placeholder secrets check

### Fix Applied:
- Commit `e08dccd`: Fixed import order, added noqa for intentional E402
- All lint checks now passing

### Next CI Run:
Should be green after commit e08dccd is pushed.

---

## 🛠️ Tasks to Complete

### Phase 1: Clean Up PRs (Priority)
1. **Review PR #42** (langchain-chroma 0.2→1.1.0)
   - Major version bump - check if compatible with langchain>=0.3.0
   - Test locally if unsure
   - If compatible → merge, if not → close with explanation

2. **Review PR #43** (tiktoken 0.5→0.12.0)
   - Major version bump - check for breaking changes
   - Verify OpenAI compatibility
   - If compatible → merge, if not → close with explanation

3. **Review remaining Dependabot PRs (#38-41, #44-48)**
   - Frontend deps: Check package.json - most use `^` so will get updates automatically
   - Backend deps: Check if version pin needs update
   - Close if already satisfied by current constraints
   - Merge if actual security fix or needed feature

4. **For each closed PR:**
   - If bot PR: Mark as "applied locally" in comments
   - If human PR: Ensure proper credit given

### Phase 2: Deploy Backend to Render
1. **Pre-deployment checklist:**
   - [ ] Verify `render.yaml` exists and is correct
   - [ ] Check Docker image is buildable
   - [ ] Confirm environment variables needed

2. **Environment variables (Render):**
   ```
   API_ACCESS_KEY=<generate-secure-key>
   OPENAI_API_KEY=<your-key>
   ANTHROPIC_API_KEY=<your-key>
   GOOGLE_API_KEY=<your-key>
   DEFAULT_PROVIDER=openai
   DEFAULT_MODEL=gpt-4o-mini
   CORS_ALLOW_ORIGINS=https://realestate-web.onrender.com,https://ai-real-estate-assistant.vercel.app
   ENVIRONMENT=production
   ```

3. **Deploy steps:**
   - Log into Render dashboard
   - Connect repository (if not connected)
   - Deploy `realestate-api` service
   - Set environment variables (sync: false - manual entry required)
   - Verify health: `curl https://realestate-api.onrender.com/health`

### Phase 3: Deploy Frontend to Vercel
1. **Pre-deployment checklist:**
   - [ ] `apps/web/vercel.json` exists ✅ (already created)
   - [ ] Verify build works: `cd apps/web && npm run build`
   - [ ] Check API proxy configuration

2. **Deploy steps:**
   ```bash
   cd apps/web
   vercel login
   vercel --prod
   ```

3. **Environment variables (Vercel):**
   ```
   NEXT_PUBLIC_API_URL=/api/v1
   BACKEND_API_URL=https://realestate-api.onrender.com/api/v1
   API_ACCESS_KEY=<same-as-backend>
   ```

### Phase 4: Post-Deployment Verification
1. **Backend health:**
   ```bash
   curl https://realestate-api.onrender.com/health
   curl https://realestate-api.onrender.com/docs
   ```

2. **Frontend load:**
   - Visit deployed URL
   - Test page navigation
   - Check console for errors

3. **API proxy:**
   - Test `/api/v1/properties/search` through frontend
   - Verify CORS headers
   - Check authentication flow

4. **Integration smoke test:**
   - Property search query
   - Agent interaction
   - Mortgage calculation tool

---

## 🔑 Environment Variables Reference

### Current (.env):
```bash
ENVIRONMENT=development
CORS_ALLOW_ORIGINS=http://localhost:3000
API_ACCESS_KEY=dev-secret-key
GITHUB_PERSONAL_ACCESS_TOKEN=ghp_**** (check .env)
ZAI_API_KEY=532****.laZehcCLc6LQBQJP (check .env)
ZHIPUAI_API_KEY=8af****.QZcicDLT2AWUKLtA (check .env)
```

### Needed for Production:
- `API_ACCESS_KEY` - Generate secure key
- `OPENAI_API_KEY` or other LLM provider
- `CORS_ALLOW_ORIGINS` - Production frontend URLs

---

## 📁 Key Files

| File | Purpose |
|------|---------|
| `render.yaml` | Backend deployment config (Render.com) |
| `apps/web/vercel.json` | Frontend deployment config (Vercel) |
| `.github/workflows/ci.yml` | CI/CD pipeline |
| `apps/api/pyproject.toml` | Python dependencies |
| `apps/web/package.json` | Node.js dependencies |
| `apps/api/core/jwt.py` | JWT security (fixed) |
| `scripts/ci/coverage_gate.py` | XXE vulnerability (fixed) |

---

## 🧪 Commands Reference

```bash
# Development
make dev                    # Auto-detect Docker or local
make dev-api                # Backend only
make dev-web                # Frontend only

# Testing
make test                   # All tests
cd apps/api && pytest tests/unit tests/integration -n auto
cd apps/web && npm test

# Linting
make lint
make format
ruff check apps/api
cd apps/web && npm run lint

# CI/CD
make ci                      # Full CI locally
make security                # All security scans

# Deployment prep
cd apps/web && vercel login
vercel --prod
```

---

## 🎤 Credit Given to Contributors

### @KrabbiAI (krabbi@openclaw.ai)
- **PR #32:** Critical security fixes
- JWT signature bypass (CVSS 9.1)
- XXE vulnerability prevention (CVSS 7.5)
- Thank you: https://github.com/AleksNeStu/ai-real-estate-assistant/pull/32#issuecomment-4375705243

### @Jwrede
- **PR #37:** Tokentoll LLM cost analysis
- Automated cost tracking for PRs
- Thank you: https://github.com/AleksNeStu/ai-real-estate-assistant/pull/37#issuecomment-4375706251

---

## 📝 Notes for New Session

### What's Been Done:
1. ✅ JWT security fix applied (commit eec6977, merged in PR #32)
2. ✅ XXE vulnerability fix (commit 1cd4886, merged in PR #32)
3. ✅ Dependencies updated (14/15 Dependabot PRs)
4. ✅ Lint errors fixed (commit e08dccd)
5. ✅ Thank you comments posted to human contributors
6. ✅ Vercel config created (`apps/web/vercel.json`)

### What's Left:
1. ⏳ Review and handle 11 new Dependabot PRs
2. ⏳ Deploy backend to Render.com
3. ⏳ Deploy frontend to Vercel
4. ⏳ Post-deployment verification

### GitHub MCP Server:
- **Currently NOT WORKING** - hardcoded binary path in `.mcp.json`
- Needs fix to comply with infrastructure rules
- Not blocking for deployment

### MCP Configuration Issue:
```json
{
  "dev-github": {
    "command": "C:/Users/he/.gemini/antigravity/servers/bin/ps-github-go.exe",  // ❌ Hardcoded path
    "args": ["stdio", "--toolsets=default,discussions"],
    "env": {
      "GITHUB_TOKEN": "${GITHUB_PERSONAL_ACCESS_TOKEN}"
    }
  }
}
```

Should use standard command like `"npx"` or `"uvx"` instead.

---

## 🚀 Ready to Deploy

All security fixes applied, lint passing, human contributors credited. Ready for production deployment once remaining PRs are reviewed.

**Next step:** Review PRs #42 and #43 (major version bumps) first, then handle remaining minor updates.
