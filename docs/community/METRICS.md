# Community Health Metrics

## Overview

This document defines the community health metrics tracked for the AI Real Estate Assistant Community Edition (CE). These metrics align with the project roadmap goals and help measure project growth and engagement.

## Target Metrics (Roadmap Goals)

| Metric | Target | Timeline |
|--------|--------|----------|
| GitHub Stars | >= 100 | 6 months post-launch |
| First External PR Merged | >= 1 | 3 months post-launch |
| Doc Site Visits Growth | Month-over-month increase | Ongoing |
| GitHub Issues (good first issue) | >= 5 open at any time | Ongoing |
| Fork Count | >= 20 | 6 months post-launch |
| Contributors (external) | >= 3 | 6 months post-launch |

## Weekly Tracking

### GitHub Repository Metrics

Collected weekly (every Monday) from GitHub Insights:

| Metric | Source | Collection Method |
|--------|--------|-------------------|
| Stars | `github.com/AleksNeStu/ai-real-estate-assistant` | Manual or GitHub API |
| Forks | GitHub Insights | Manual or GitHub API |
| Open Issues | GitHub Issues tab | Manual |
| Closed Issues (weekly) | GitHub Insights | Manual |
| Open PRs | GitHub PRs tab | Manual |
| Merged PRs (weekly) | GitHub Insights | Manual |
| Unique Contributors | GitHub Contributors graph | Manual |

### Collection via GitHub CLI

```bash
# Stars and forks
gh repo view AleksNeStu/ai-real-estate-assistant --json stargazerCount,forkCount

# Open issues with "good first issue" label
gh issue list --repo AleksNeStu/ai-real-estate-assistant --label "good first issue" --state open

# Recent PRs
gh pr list --repo AleksNeStu/ai-real-estate-assistant --state all --limit 10

# Contributors
gh api repos/AleksNeStu/ai-real-estate-assistant/contributors --jq '.[].login'
```

## External PR Tracking

Track every community pull request:

| Data Point | Description |
|------------|-------------|
| PR Number | GitHub PR # |
| Author | GitHub username |
| Opened Date | When the PR was submitted |
| Merged Date | When it was merged (or "Open"/"Closed") |
| Time to Merge | Days from open to merge |
| Issue Link | Associated issue number |
| Category | Connector / UI / Docs / Bug fix |

### Time-to-First-Review SLA

- External PRs should receive initial review within **48 hours**
- Follow-up review within **24 hours** after author response
- Target merge within **7 days** for "good first issue" PRs

## Monthly Community Health Report

A monthly report is generated using the template at `docs/community/monthly-report-template.md`.

Reports are stored at: `docs/community/reports/YYYY-MM.md`

### Key Monthly Indicators

1. **Star Growth Rate**: New stars this month / total stars
2. **PR Velocity**: Average time from PR open to merge
3. **Issue Resolution Rate**: Issues closed / issues opened
4. **Community Engagement**: Unique commenters on issues/PRs
5. **Documentation Visits**: (if analytics enabled) Page views on docs

## Data Storage

- Weekly snapshots stored in this repo at `docs/community/data/weekly-snapshots.json`
- Monthly reports at `docs/community/reports/YYYY-MM.md`
- No external analytics services required (GitHub-native)

## Automation Opportunities

Future improvements (contributions welcome):

- [ ] GitHub Action to collect weekly metrics automatically
- [ ] Dashboard generation from snapshot data
- [ ] Slack/Discord notification on milestones
- [ ] Badge integration (stars, contributors) in README
