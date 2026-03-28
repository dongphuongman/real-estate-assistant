# PRD-to-TaskMaster Gap Analysis & Task Creation Plan

**Date:** 2026-03-28
**Status:** Planning complete — 28 tasks created in TaskMaster

## Context

The AI Real Estate Assistant has 65 TaskMaster tasks (64 done, 1 in-progress: #33 Deploy). Cross-referencing PRD V4, Feature Ideas, Global Roadmap, SPRAV framework, and codebase reveals **28 gaps**. This plan separates them into **CE (Community Edition — stabilize now)** and **[private] (Hosted Pro — deferred for private repo)**.

**License decision**: Keep MIT (user decision — eliminates file discord, simpler for sponsors, honest to existing code).

---

## Scope Split

| Scope | Count | Action |
|-------|-------|--------|
| CE (Community Edition) | 16 | Active tasks, work now to stabilize |
| [private] (Hosted Pro) | 12 | Deferred, with `[private]` prefix in TaskMaster |

---

## CE Tasks — Stabilize Now (16 tasks)

### Phase 1: PRD Compliance (Critical/High)

#### #90 — [CE] License Reconciliation → Keep MIT
- **Priority**: Critical | **Effort**: 0.5-1 day | **Dependencies**: None
- **Why**: PRD says AGPLv3 but LICENSE is MIT. Decision: Keep MIT, update PRD to match.
- **Acceptance Criteria**:
  1. PRD updated: AGPLv3 → MIT
  2. ADR-0009 documents decision (Keep MIT with rationale)
  3. All `package.json` license fields verified as MIT
  4. CONTRIBUTING.md license reference verified

#### #91 — [CE] WCAG 2.1 AA Accessibility Compliance
- **Priority**: Critical | **Effort**: 5-8 days | **Dependencies**: None
- **Why**: PRD mandates "WCAG 2.1 AA for interactive controls, focus management, labels, error feedback"
- **Subtasks**:
  1. axe-core integration in Jest/Playwright
  2. Chat page accessibility audit (labels, roles, live regions for streaming)
  3. Search page accessibility audit (filter controls, result cards, map)
  4. Settings/analytics/knowledge pages audit
  5. Keyboard focus management across route transitions
  6. Manual screen reader validation (NVDA/VoiceOver)
- **Acceptance Criteria**:
  1. All interactive controls have ARIA labels/roles
  2. Focus management on route changes
  3. Form inputs with labels + screen reader error feedback
  4. Color contrast 4.5:1 (text) / 3:1 (large)
  5. Keyboard navigation to all elements
  6. `axe-core` scan: 0 violations on all pages

#### #92 — [CE] Lighthouse >=90 CI Enforcement
- **Priority**: Critical | **Effort**: 2-3 days | **Dependencies**: #91
- **Why**: `lighthouse.config.js` has correct assertions but CI never runs it
- **Files**: `.github/workflows/ci.yml`, `apps/web/lighthouse.config.js`
- **Acceptance Criteria**:
  1. CI Lighthouse audit step after frontend build
  2. Blocks PR on score regression
  3. Search + chat pages >= 90 performance/accessibility
  4. Report uploaded as CI artifact

#### #93 — [CE] 5-Minute Quickstart Documentation
- **Priority**: High | **Effort**: 3-4 days | **Dependencies**: None
- **Why**: Roadmap calls for "Run your AI realtor in 5 minutes" — current quickstart is multi-path
- **Acceptance Criteria**:
  1. Single-page guide: clone → .env → docker up → working in <=5 min
  2. Pre-built Docker images on GHCR
  3. Minimal `.env.example` (1 LLM key)
  4. Smoke test script verifying stack
  5. Linked from README.md

#### #94 — [CE] Telegram Connector Community Issue
- **Priority**: High | **Effort**: 1 day | **Dependencies**: None
- **Why**: Roadmap: "create Telegram connector issue for community contribution"
- **Acceptance Criteria**:
  1. GitHub Issue with `good first issue` + `community` labels
  2. Architectural guidance + MCP connector reference
  3. Linked from CONTRIBUTING.md

### Phase 2: Production Readiness (High/Medium)

#### #95 — [CE] Audit Logging System
- **Priority**: High | **Effort**: 3-4 days | **Dependencies**: None
- **Why**: PRD NFR Security requires "audit logs"
- **Acceptance Criteria**:
  1. Audit records for admin actions (ingest, reindex, settings changes)
  2. Auth event logging (login, logout, failed attempts)
  3. Append-only, tamper-evident entries
  4. Admin query endpoint (time-range, action-type filters)
  5. Correlation with X-Request-ID

#### #96 — [CE] Graceful Degradation Testing
- **Priority**: High | **Effort**: 3-5 days | **Dependencies**: None
- **Why**: PRD requires degradation when providers/vector store unavailable
- **Acceptance Criteria**:
  1. ChromaDB down → search error, chat reduced capability
  2. All LLMs down → friendly message with retry
  3. Single provider fail → automatic fallback
  4. DB down → health reports degraded
  5. Circuit breaker for external calls

#### #97 — [CE] Versioned API Contract Enforcement
- **Priority**: High | **Effort**: 3-4 days | **Dependencies**: None
- **Why**: PRD requires "versioned endpoints" with no breaking-change detection
- **Acceptance Criteria**:
  1. OpenAPI diff CI step detects breaking changes
  2. API versioning ADR documented
  3. Response headers include API version
  4. Backward compatibility test suite

#### #98 — [CE] Structured Log Standardization
- **Priority**: High | **Effort**: 2-3 days | **Dependencies**: #81 (done)
- **Why**: PRD requires "structured logs, traces, metrics, request IDs"
- **Acceptance Criteria**:
  1. All logs JSON with required fields (timestamp, level, request_id, service, message)
  2. Log level policy documented
  3. No sensitive data in logs (automated verification)
  4. Frontend errors include request_id

#### #99 — [CE] Full E2E Test Suite in CI
- **Priority**: High | **Effort**: 5-7 days | **Dependencies**: None
- **Why**: Sprint 4 calls for "Full e2e tests." E2E exists but doesn't run in CI
- **Acceptance Criteria**:
  1. E2E covers all user flows (search, chat, tools, settings, auth, exports)
  2. E2E runs in CI (separate job)
  3. Results as CI artifacts
  4. Flaky rate < 5%

#### #100 — [CE] SPRAV Pre-Release Full Validation Run
- **Priority**: High | **Effort**: 2-3 days | **Dependencies**: #95-#99
- **Why**: SPRAV framework exists, Task #33 blocked, full validation needed before deploy
- **Acceptance Criteria**:
  1. `make sprav` completes with 0 blockers
  2. Backend unit coverage >= 90% critical paths
  3. Backend integration coverage >= 70%
  4. Security: 0 secrets, 0 high-confidence vulns
  5. Alembic migration validated
  6. Report in `artifacts/validation_report.md`

#### #101 — [CE] Alembic Migration Data Population
- **Priority**: Medium | **Effort**: 1-2 days | **Dependencies**: None
- **Why**: Fresh Alembic migration (March 27). No seed strategy.
- **Acceptance Criteria**:
  1. Idempotent seed script for dev/demo data
  2. Docker Compose runs migration + seed automatically
  3. Data population docs

#### #102 — [CE] npm Vulnerability Ongoing Monitoring
- **Priority**: Medium | **Effort**: 1 day | **Dependencies**: #89 (done)
- **Why**: #89 fixed current vulns but no ongoing gate
- **Acceptance Criteria**:
  1. `npm audit` CI step fails on high/critical
  2. Dependabot/Renovate configured

### Phase 3: Community Launch (High/Medium)

#### #103 — [CE] Community Contribution Guidelines Enhancement
- **Priority**: High | **Effort**: 2-3 days | **Dependencies**: #90
- **Acceptance Criteria**:
  1. CONTRIBUTING.md with CE-specific sections
  2. PR template with CE compliance checklist
  3. 5+ issues labeled `good first issue`
  4. DCO/CLA requirement documented

#### #104 — [CE] Community Metrics Dashboard
- **Priority**: Medium | **Effort**: 2-3 days | **Dependencies**: None
- **Acceptance Criteria**: GitHub stars tracking, external PR tracking, monthly health report template

#### #105 — [CE] API Reference Completeness Audit
- **Priority**: Medium | **Effort**: 3-4 days | **Dependencies**: None
- **Acceptance Criteria**: All `/api/v1/*` in OpenAPI + markdown, drift checks pass

---

## [private] Tasks — Deferred for Private Repo (12 tasks)

All created with `[private]` prefix, status: **deferred**, Low priority.

#### #106 — [private] Success Metrics Tracking Infrastructure
- **Priority**: Low | **Effort**: 5-7 days | **Dependencies**: #82, #81 (both done)
- **Why**: PRD defines 4 Success Metrics (engagement, relevance, conversion, performance) — Pro/hosted scope

#### #107 — [private] Dynamic Pricing & Market Positioning
- **Priority**: Low | **Effort**: 8-10 days | **Dependencies**: #38, #85 (both done)
- **Why**: FEATURE_IDEAS — agent-facing tool

#### #108 — [private] Negotiation Helper
- **Priority**: Low | **Effort**: 5-7 days | **Dependencies**: #107, #85
- **Why**: FEATURE_IDEAS — agent-facing tool

#### #109 — [private] Personalised Recommendations Engine
- **Priority**: Low | **Effort**: 7-10 days | **Dependencies**: #37, #82 (both done)
- **Why**: FEATURE_IDEAS — Pro feature

#### #110 — [private] Shared Shortlists
- **Priority**: Low | **Effort**: 5-7 days | **Dependencies**: #37 (done)
- **Why**: FEATURE_IDEAS — Pro collaboration feature

#### #111 — [private] CRM Integration (HubSpot/Pipedrive)
- **Priority**: Low | **Effort**: 8-12 days | **Dependencies**: #55, #45 (both done)
- **Why**: FEATURE_IDEAS — Pro integration

#### #112 — [private] Calendar Integration for Viewings
- **Priority**: Low | **Effort**: 3-5 days | **Dependencies**: None
- **Why**: FEATURE_IDEAS — Pro scheduling feature

#### #113 — [private] BI Export Pipelines
- **Priority**: Low | **Effort**: 5-7 days | **Dependencies**: #80 (done)
- **Why**: FEATURE_IDEAS — Pro data team feature

#### #114 — [private] Portfolio Vacancy & Absorption Analytics
- **Priority**: Low | **Effort**: 5-7 days | **Dependencies**: #39, #56 (both done)
- **Why**: FEATURE_IDEAS — Pro manager analytics

#### #115 — [private] Multi-Agent Orchestration Framework
- **Priority**: Low | **Effort**: 10-15 days | **Dependencies**: None
- **Why**: PRD Hosted Pro scope — "lead qualification, legal analysis"

#### #116 — [private] Voice Mode with Telephony
- **Priority**: Low | **Effort**: 15-20 days | **Dependencies**: None
- **Why**: PRD Hosted Pro scope

#### #117 — [private] Dialog Efficiency & Conversion Analytics
- **Priority**: Low | **Effort**: 5-7 days | **Dependencies**: #106
- **Why**: PRD Hosted Pro — "analytics dashboard for dialog efficiency and conversion"

---

## Dependency Graph

```
CE Phase 1 (Critical):
  #90 (License → MIT) ────> #103 (Contributing)
  #91 (WCAG 2.1 AA) ────> #92 (Lighthouse CI)
  #93 (Quickstart) ── independent
  #94 (Telegram Issue) ── independent

CE Phase 2 (High):
  #95-#99 (NFRs) ── independent, can parallel
  #100 (SPRAV) ── depends on #95, #96, #97, #98, #99
  #101 (Alembic Data) ── independent
  #102 (npm Monitoring) ── independent

CE Phase 3 (High-Medium):
  #103 (Contributing) ── depends on #90
  #104 (Community Metrics) ── independent
  #105 (API Reference) ── independent

Task #33 (Deploy) ── blocked by CE Phase 1 + Phase 2

[private] tasks: all deferred, no immediate execution
```

---

## Task Status Summary

| Task | Title | Status | Priority |
|------|-------|--------|----------|
| #90 | [CE] License Reconciliation → Keep MIT | pending | Critical |
| #91 | [CE] WCAG 2.1 AA Accessibility Compliance | pending | Critical |
| #92 | [CE] Lighthouse >=90 CI Enforcement | pending | Critical |
| #93 | [CE] 5-Minute Quickstart Documentation | pending | High |
| #94 | [CE] Telegram Connector Community Issue | pending | High |
| #95 | [CE] Audit Logging System | pending | High |
| #96 | [CE] Graceful Degradation Testing | pending | High |
| #97 | [CE] Versioned API Contract Enforcement | pending | High |
| #98 | [CE] Structured Log Standardization | pending | High |
| #99 | [CE] Full E2E Test Suite in CI | pending | High |
| #100 | [CE] SPRAV Pre-Release Full Validation Run | pending | High |
| #101 | [CE] Alembic Migration Data Population | pending | Medium |
| #102 | [CE] npm Vulnerability Ongoing Monitoring | pending | Medium |
| #103 | [CE] Community Contribution Guidelines | pending | High |
| #104 | [CE] Community Metrics Dashboard | pending | Medium |
| #105 | [CE] API Reference Completeness Audit | pending | Medium |
| #106 | [private] Success Metrics Tracking | deferred | Low |
| #107 | [private] Dynamic Pricing & Market Positioning | deferred | Low |
| #108 | [private] Negotiation Helper | deferred | Low |
| #109 | [private] Personalised Recommendations Engine | deferred | Low |
| #110 | [private] Shared Shortlists | deferred | Low |
| #111 | [private] CRM Integration | deferred | Low |
| #112 | [private] Calendar Integration for Viewings | deferred | Low |
| #113 | [private] BI Export Pipelines | deferred | Low |
| #114 | [private] Portfolio Vacancy & Absorption Analytics | deferred | Low |
| #115 | [private] Multi-Agent Orchestration Framework | deferred | Low |
| #116 | [private] Voice Mode with Telephony | deferred | Low |
| #117 | [private] Dialog Efficiency & Conversion Analytics | deferred | Low |

---

## Recommended Execution Order

1. **#90** — License reconciliation (0.5 day, unblocks #103)
2. **#93** — Quickstart docs (independent, high value)
3. **#94** — Telegram community issue (independent, quick win)
4. **#91** — WCAG accessibility (5-8 days, unblocks #92)
5. **#92** — Lighthouse CI (depends on #91)
6. **#95-#99** — NFR tasks (parallel, 2-7 days each)
7. **#101** — Alembic seed data (independent)
8. **#102** — npm monitoring (independent)
9. **#100** — SPRAV full validation (depends on #95-#99)
10. **#103** — Community guidelines (depends on #90)
11. **#104, #105** — Community launch (independent)
12. **#33** — Deploy (after Phase 1 + Phase 2)

---

## Note on TaskMaster Data

`.taskmaster/` is gitignored (local-only). All 28 tasks are in the local TaskMaster database. This document serves as the persistent reference for the task definitions.
