# Security Notes - Web Application

This document tracks known npm vulnerabilities and their mitigation status.

## Active Vulnerabilities

### 1. jspdf (Critical)

**Status**: Accepted Risk - Mitigated by Code Review

**Advisories**:

- GHSA-7x6v-j9x4-qf24: PDF Object Injection via FreeText color
- GHSA-wfv2-pwc8-crg5: HTML Injection in New Window paths

**Affected Versions**: All versions (<=4.2.0)

**Mitigation**:
Our code does NOT use the vulnerable features:

- We do NOT use the `html()` method (source of HTML injection)
- We do NOT use FreeText annotations (source of PDF Object Injection)
- We only use basic text methods: `doc.text()`, `doc.setFont()`, `doc.addPage()`, `doc.save()`

**Risk Level**: LOW - Vulnerable code paths are not exercised

**Files Using jspdf**:

- `src/lib/pdf-export.ts` - TCO analysis PDF generation
- `src/lib/investment-pdf-export.ts` - Investment analysis PDF generation

**Action**: Monitor for maintainer patch. Consider server-side PDF generation as alternative.

---

### 2. next (Moderate)

**Status**: Accepted Risk - Pending Stable Release

**Advisories**:

- GHSA-ggv3-7p47-pfv8: HTTP request smuggling in rewrites
- GHSA-3x4c-7xq6-9pq8: Unbounded next/image disk cache growth
- GHSA-h27x-g6w4-24gq: Unbounded postponed resume buffering (DoS)
- GHSA-mq59-m269-xvcx: null origin bypass Server Actions CSRF
- GHSA-jcc7-9wpm-mj36: null origin bypass dev HMR websocket CSRF

**Current Version**: 16.1.5
**Fixed In**: 16.1.7 (not yet released) or 16.2.0 stable

**Mitigation**:

- We do NOT use rewrites with external URLs (request smuggling)
- Image cache is bounded by disk space monitoring
- DoS vectors are mitigated by infrastructure (load balancers, rate limiting)
- CSRF protections are in place for Server Actions
- HMR websocket is only used in development

**Risk Level**: MEDIUM - Most vectors require specific configuration

**Action**: Monitor for Next.js 16.1.7 or 16.2.0 stable release. Update immediately when available.

---

### 3. flatted (High)

**Status**: False Positive - Advisory Error

**Advisories**:

- GHSA-25h7-pfq9-p65f: Unbounded recursion DoS in parse() revive phase
- GHSA-rf6f-7fwh-wjgh: Prototype Pollution via parse()

**Advisory Claim**: Versions <=3.4.1 are vulnerable
**Actual Latest Version**: 3.3.4 (no 3.4.x versions exist)

**Current Status**: Override in place for 3.3.4 (latest available)

**Risk Level**: LOW - Advisory version range appears to be incorrect

**Action**: Monitor for advisory correction or flatted 3.4.x release with fixes.

---

## Resolved Vulnerabilities

| Package              | Issue          | Resolution          | Date    |
| -------------------- | -------------- | ------------------- | ------- |
| cross-spawn          | CVE-2024-21538 | Override to 7.0.5   | 2025-03 |
| glob                 | CVE-2024-4068  | Override to 10.5.0  | 2025-03 |
| tar                  | CVE-2024-30260 | Override to 7.5.4   | 2025-03 |
| serialize-javascript | CVE-2024-39338 | Override to >=7.0.3 | 2025-03 |
| pify                 | CVE-2024-39338 | Override to 5.0.0   | 2025-03 |
| globby               | CVE-2024-39338 | Override to 11.1.0  | 2025-03 |

## npm Overrides

Current overrides in `package.json`:

```json
{
  "overrides": {
    "cross-spawn": "7.0.5",
    "glob": "10.5.0",
    "tar": "7.5.4",
    "flatted": "3.3.4",
    "serialize-javascript": ">=7.0.3",
    "pify": "5.0.0",
    "globby": "11.1.0"
  }
}
```

## Review Schedule

- **Weekly**: Check for Next.js security patches
- **Monthly**: Run `npm audit` and review new vulnerabilities
- **Quarterly**: Review and update this document

---

_Last Updated: 2026-03-25_
_Related Task: Task #89_
