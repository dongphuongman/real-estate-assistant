# SPRAV Report: [RELEASE_VERSION]

**Date:** [YYYY-MM-DD]
**Release:** [VERSION/TAG]
**Team Lead:** [NAME]
**Overall Status:** [GO / NO-GO / CONDITIONAL]

---

## Executive Summary

- **Total Validations Executed:** [N]
- **Passed:** [N]
- **Failed:** [N]
- **Blocked:** [N]
- **Skipped:** [N]

### Recommendation

**[GO / NO-GO / CONDITIONAL]**

[Summary paragraph explaining the recommendation and any conditions]

---

## Validation Results Matrix

| Category | Status | Pass | Fail | Block | Owner |
|----------|--------|------|------|-------|-------|
| Functional | [✓/✗] | [N] | [N] | [N] | QA |
| Non-Functional | [✓/✗] | [N] | [N] | [N] | Backend |
| Architectural | [✓/✗] | [N] | [N] | [N] | Architect |
| Business | [✓/✗] | [N] | [N] | [N] | Analyst |
| Security | [✓/✗] | [N] | [N] | [N] | Automation |
| Performance | [✓/✗] | [N] | [N] | [N] | Backend |

---

## Detailed Results by Role

### 1. Automation Engineer

| Check | Status | Details |
|-------|--------|---------|
| Security scans (Gitleaks) | [✓/✗] | [Details] |
| Security scans (Semgrep) | [✓/✗] | [Details] |
| Security scans (Bandit) | [✓/✗] | [Details] |
| Security scans (pip-audit) | [✓/✗] | [Details] |
| Docker build | [✓/✗] | [Details] |
| Docker smoke test | [✓/✗] | [Details] |

### 2. Architect

| Check | Status | Details |
|-------|--------|---------|
| Backend lint (ruff) | [✓/✗] | [Details] |
| Frontend lint (ESLint) | [✓/✗] | [Details] |
| OpenAPI schema drift | [✓/✗] | [Details] |
| Type checking (mypy) | [✓/✗] | [Details] |
| Code complexity | [✓/✗] | [Details] |

### 3. QA Engineer

| Check | Status | Details |
|-------|--------|---------|
| Unit test coverage (>=90%) | [✓/✗] | [Actual: X%] |
| Integration test coverage (>=70%) | [✓/✗] | [Actual: X%] |
| Frontend coverage (>=85%) | [✓/✗] | [Actual: X%] |
| User journey tests | [✓/✗] | [Details] |
| Edge case tests | [✓/✗] | [Details] |

### 4. Backend Developer

| Check | Status | Details |
|-------|--------|---------|
| API endpoints | [✓/✗] | [Details] |
| Rate limiting | [✓/✗] | [Details] |
| Authentication | [✓/✗] | [Details] |
| Database operations | [✓/✗] | [Details] |
| Caching | [✓/✗] | [Details] |

### 5. Frontend Developer

| Check | Status | Details |
|-------|--------|---------|
| Build succeeds | [✓/✗] | [Details] |
| TypeScript check | [✓/✗] | [Details] |
| Cross-browser | [✓/✗] | [Details] |
| Accessibility | [✓/✗] | [Details] |
| Responsive design | [✓/✗] | [Details] |

### 6. Business Analyst

| Check | Status | Details |
|-------|--------|---------|
| Core user journeys | [✓/✗] | [Details] |
| Feature acceptance | [✓/✗] | [Details] |
| Regression check | [✓/✗] | [Details] |

---

## Test Evidence

### Coverage Reports

| Report | Path | Summary |
|--------|------|---------|
| Backend Unit | `artifacts/backend-coverage-unit-xml/coverage.xml` | [X% lines] |
| Backend Integration | `artifacts/backend-coverage-integration-xml/coverage.xml` | [X% lines] |
| Frontend | `apps/web/coverage/coverage-summary.json` | [X% lines] |

### Security Reports

| Scan | Status | Report Path |
|------|--------|-------------|
| Gitleaks | [✓/✗] | [Path] |
| Semgrep | [✓/✗] | `artifacts/semgrep-report.json` |
| Bandit | [✓/✗] | `artifacts/bandit.json` |
| pip-audit | [✓/✗] | `artifacts/pip-audit.json` |

### Performance Metrics

| Metric | Value | Threshold | Status |
|--------|-------|-----------|--------|
| API Response Time (p95) | [X]ms | <500ms | [✓/✗] |
| API Response Time (p99) | [X]ms | <1000ms | [✓/✗] |
| Docker Health Check | [X]s | <30s | [✓/✗] |
| Frontend Build Time | [X]s | <120s | [✓/✗] |

---

## Defect Log

| ID | Severity | Priority | Component | Description | Status | Owner |
|----|----------|----------|-----------|-------------|--------|-------|
| D001 | [Critical/High/Medium/Low] | P1/P2/P3/P4 | [Component] | [Description] | Open/Fixed/Deferred | [Name] |
| D002 | ... | ... | ... | ... | ... | ... |

**Summary:**
- Critical: [N]
- High: [N]
- Medium: [N]
- Low: [N]

---

## Risk Assessment

| Risk ID | Description | Probability | Impact | Mitigation | Owner |
|---------|-------------|-------------|--------|------------|-------|
| R001 | [Risk description] | High/Med/Low | High/Med/Low | [Mitigation plan] | [Name] |
| R002 | ... | ... | ... | ... | ... |

**Risk Matrix:**
```
           │ LOW    │ MEDIUM │ HIGH   │ CRITICAL
───────────┼────────┼────────┼────────┼─────────
CRITICAL   │ MED    │ HIGH   │ CRIT   │ CRIT
HIGH       │ MED    │ HIGH   │ CRIT   │ CRIT
MEDIUM     │ LOW    │ MED    │ HIGH   │ HIGH
LOW        │ LOW    │ LOW    │ MED    │ MED
```

---

## GO Criteria Checklist

- [ ] All automated tests pass (`make ci` succeeds)
- [ ] No Critical or High severity defects open
- [ ] Coverage gates met (90% unit, 70% integration)
- [ ] Security scans pass (0 secrets, 0 high-confidence issues)
- [ ] Docker deployment succeeds with health checks
- [ ] Core user journeys validated
- [ ] API documentation up to date
- [ ] Rollback procedure tested

## NO-GO Criteria Checklist

- [ ] Any Critical defect unresolved
- [ ] Security vulnerability with known exploit
- [ ] Coverage below thresholds
- [ ] Docker deployment fails
- [ ] Core functionality broken
- [ ] API contract breaking changes without migration

---

## Sign-Off

| Role | Name | Signature | Date |
|------|------|-----------|------|
| Team Lead | | | |
| Architect | | | |
| QA Engineer | | | |
| Business Analyst | | | |
| Automation Engineer | | | |
| Frontend Developer | | | |
| Backend Developer | | | |

---

## Appendix

### A. Test Commands Executed

```bash
# Full CI pipeline
make ci

# Security scans
make security

# Backend tests
cd apps/api && pytest tests/unit tests/integration --cov=. --cov-report=term -n auto

# Frontend tests
cd apps/web && npm run test:ci

# Docker smoke test
python scripts/docker/compose_smoke.py --timeout-seconds 600
```

### B. Environment Details

- **OS:** [Windows/Linux/macOS]
- **Python:** [3.12.x]
- **Node.js:** [20.x]
- **Docker:** [24.x]
- **Database:** [PostgreSQL/SQLite]

### C. Known Issues / Technical Debt

| ID | Description | Impact | Planned Resolution |
|----|-------------|--------|-------------------|
| TD001 | [Description] | [Impact] | [Sprint/Version] |

---

*Generated by SPRAV Framework v1.0.0*
*Template Version: 1.0.0*
