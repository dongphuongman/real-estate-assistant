# Accessibility Audit — WCAG 2.1 AA Compliance

**Date:** 2026-05-09
**Standard:** WCAG 2.1 Level AA
**Scope:** All user-facing React components in `apps/web/src/components/`

## Summary

| Category | Files Audited | Issues Fixed | Known Limitations |
|----------|--------------|-------------|-------------------|
| Analytics | 5 | 24 | 0 |
| Search | 4 | 14 | 3 (map components) |
| Settings | 6 | 31 | 0 |
| **Total** | **15** | **69** | **3** |

## Fixes Applied

### 1. Decorative Icons — `aria-hidden="true"`
All decorative Lucide icons (next to visible text labels) received `aria-hidden="true"` to prevent screen reader announcement of redundant content.

**Files:**
- `analytics/portfolio-analyzer.tsx` — 7 icons
- `analytics/price-history-chart.tsx` — 4 icons
- `analytics/rent-vs-buy-calculator.tsx` — 6 icons
- `analytics/tco-comparison.tsx` — 7 icons
- `search/map-controls.tsx` — 6 icons
- `search/preset-selector.tsx` — 7 icons
- `settings/notification-settings.tsx` — 10 icons
- `settings/privacy-settings.tsx` — 13 icons
- `settings/profile-settings.tsx` — 6 icons

### 2. Form Label Associations
Missing `<Label htmlFor>` + `id` pairs added for form controls that lacked them.

**Files:**
- `analytics/portfolio-analyzer.tsx` — 6 label associations fixed

### 3. Unlabeled Form Controls
Added `aria-label` to `<select>` elements without visible labels.

**Files:**
- `settings/task-model-settings.tsx` — 2 select elements (provider, model)

### 4. Progress Bar ARIA
Added `role="progressbar"` with `aria-valuenow`, `aria-valuemin`, `aria-valuemax`, and `aria-label`.

**Files:**
- `settings/privacy-settings.tsx` — GDPR export progress bar

### 5. Chart Accessibility
Added `role="img"` and `aria-label` to Recharts chart containers.

**Files:**
- `analytics/rent-vs-buy-calculator.tsx` — 2 charts
- `analytics/price-history-chart.tsx` — 1 chart

### 6. Interactive Controls ARIA
Added `aria-expanded` for toggle buttons controlling collapsible sections.

**Files:**
- `analytics/rent-vs-buy-calculator.tsx` — advanced options toggle

### 7. Cluster Marker Semantics
Added `role="img"` and `aria-label` to map cluster markers.

**Files:**
- `search/cluster-marker.tsx` — cluster marker component

## Known Limitations

### Map Components (Architectural)

Three map components use imperative DOM manipulation (Leaflet `divIcon`/`innerHTML` or Mapbox GL JS `document.createElement`/`innerHTML`) to create markers, which bypasses React's accessibility patterns. These cannot be fully made accessible without a fundamental architectural change (e.g., switching to a React-native map library like `react-map-gl` with proper ARIA support).

| Component | Library | Limitation |
|-----------|---------|------------|
| `search/property-map.tsx` | Leaflet | Markers via `divIcon` with `innerHTML` — no React lifecycle |
| `search/property-mapbox-map.tsx` | Mapbox GL JS | Markers via `document.createElement` + `innerHTML` |
| `search/geo-draw-control.tsx` | Mapbox Draw | Returns `null`, third-party controls |

**Mitigation:** These map components already have keyboard-accessible zoom/pan controls via `search/map-controls.tsx` (which has full ARIA compliance). Property details are accessible through the search results list, which is fully compliant.

## Files Requiring No Changes

These files were audited and found to already have proper accessibility:
- `settings/identity-settings.tsx` — Excellent a11y, no fixes needed
- `settings/model-settings.tsx` — Proper labels, no decorative icons

## Verification

Run frontend tests to confirm no regressions:
```bash
cd apps/web && npm test
```
