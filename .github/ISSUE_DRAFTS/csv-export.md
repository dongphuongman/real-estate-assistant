---
title: "Community: Add CSV Export for Property Results"
labels: good first issue, help wanted
---

## Overview

Add CSV export functionality to property search results, allowing users to download search results as a spreadsheet for offline analysis.

## Skills Required

- [x] Python (async, FastAPI)
- [ ] TypeScript/React
- [x] Testing (pytest)

## Architecture Context

The search endpoint returns property results from `apps/api/api/routers/search.py`. This task adds:

1. Backend endpoint: `GET /api/v1/search/export/csv` accepting same filters as search
2. Returns CSV with columns: title, address, price, rooms, area, url

Reference files:
- Search router: `apps/api/api/routers/search.py`
- Property schema: `apps/api/db/schemas.py`
- Data models: `apps/api/db/models.py`

## Acceptance Criteria

- [ ] New endpoint `GET /api/v1/search/export/csv` returns CSV file
- [ ] CSV includes standard property fields (title, address, price, rooms, area, url)
- [ ] UTF-8 encoding with BOM for Excel compatibility
- [ ] Respects same query filters as regular search
- [ ] Rate limited (max 10 exports per minute per user)
- [ ] Unit tests for CSV generation
- [ ] Integration test for endpoint

## Getting Started

1. Fork and clone the repository
2. Review the search router and property schemas
3. Create branch: `git checkout -b feature/csv-export`
4. Implement, test, and open a PR against `dev`

## Questions?

Comment on this issue and a maintainer will help you get started.
