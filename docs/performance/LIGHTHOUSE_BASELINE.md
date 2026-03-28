# Lighthouse CI Baseline Scores

## Audit Configuration

| Parameter | Value |
|-----------|-------|
| Tool | @lhci/cli |
| Runs per URL | 3 (median reported) |
| Desktop config | `apps/web/lighthouse.config.js` |
| LHCI config | `apps/web/lighthouserc.js` |
| CI Job | `lighthouse` (`.github/workflows/ci.yml`) |

## Audited URLs

| URL | Description |
|-----|-------------|
| `/en/search` | Property search page |
| `/en/chat` | AI chat page |

## Desktop Baseline

*Scores to be populated after first successful CI run.*

| URL | Performance | Accessibility | Best Practices | SEO |
|-----|-------------|---------------|----------------|-----|
| `/en/search` | -- | -- | -- | -- |
| `/en/chat` | -- | -- | -- | -- |

## CI Enforcement

| Metric | Threshold | Level |
|--------|-----------|-------|
| Performance (desktop) | >= 90 | error (blocks PR) |
| Accessibility (desktop) | >= 90 | error (blocks PR) |
| Best Practices (desktop) | >= 90 | warn |
| SEO (desktop) | >= 80 | warn |
| First Contentful Paint | < 2.0s | error |
| Largest Contentful Paint | < 2.5s | error |
| Cumulative Layout Shift | < 0.1 | error |
| Total Blocking Time | < 300ms | error |
| Speed Index | < 3.0s | error |

## Reports

Lighthouse HTML reports are uploaded as GitHub Actions artifacts (`lighthouse-results`) on every CI run.
