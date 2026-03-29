---
title: "Community: Add iCal Export for Saved Searches"
labels: good first issue, help wanted
---

## Overview

Add an iCal/ICS export feature that lets users download property viewing schedules as calendar events. This is a frontend-focused task with a small backend endpoint.

## Skills Required

- [ ] Python (async, FastAPI)
- [x] TypeScript/React
- [ ] Testing (Jest)
- [x] Frontend UI work

## Architecture Context

The saved searches feature already exists at `apps/web/src/contexts/FavoritesContext.tsx` and the backend at `apps/api/api/routers/saved_searches.py`. This task adds:

1. Backend endpoint: `GET /api/v1/saved-searches/{id}/export/ics` returning iCal format
2. Frontend button: "Export to Calendar" on saved search detail page

Reference files:
- Backend: `apps/api/api/routers/saved_searches.py`
- Frontend: `apps/web/src/app/saved-searches/[id]/page.tsx`

## Acceptance Criteria

- [ ] Backend endpoint returns valid iCal (.ics) file
- [ ] Each property in saved search becomes a calendar event
- [ ] Events include address, price, link to property page
- [ ] Frontend "Export to Calendar" button triggers download
- [ ] Works with Google Calendar, Apple Calendar, Outlook
- [ ] Unit tests for iCal generation

## Getting Started

1. Fork and clone the repository
2. Review the saved search router and frontend page
3. Create branch: `git checkout -b feature/ical-export`
4. Implement, test, and open a PR against `dev`

## Questions?

Comment on this issue and a maintainer will help you get started.
