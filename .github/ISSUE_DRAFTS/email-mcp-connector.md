---
title: "Community: Add Email Notification MCP Connector"
labels: good first issue, help wanted
---

## Overview

Implement an email notification MCP connector that sends property alerts and search results via email (SMTP or Sendgrid API). This is a great opportunity to learn the MCP connector pattern.

## Skills Required

- [x] Python (async, FastAPI)
- [ ] TypeScript/React
- [x] Testing (pytest)

## Architecture Context

This connector follows the `MCPConnector[T]` abstract base class pattern. It should:
1. Extend `MCPConnector` from `apps/api/mcp/base.py`
2. Implement lifecycle methods: `connect()`, `disconnect()`, `health_check()`, `execute()`
3. Register in `apps/api/mcp/registry.py`
4. Add to `apps/api/config/mcp_allowlist.yaml` under `community_edition`

Reference implementation: `apps/api/mcp/connectors/web_scraper.py`

## Expected Operations

- `send_email` - Send a property alert email to a recipient
- `send_batch` - Send batch notifications to multiple recipients
- `verify_connection` - Verify SMTP/API credentials are valid

## Acceptance Criteria

- [ ] Connector class extends `MCPConnector[EmailConfig]`
- [ ] `connect()` validates SMTP credentials or Sendgrid API key
- [ ] `execute("send_email", ...)` sends a single email with property details
- [ ] `execute("send_batch", ...)` sends batch emails with rate limiting
- [ ] `health_check()` verifies email service connectivity
- [ ] Registered in `mcp_allowlist.yaml` under `community_edition`
- [ ] Unit tests in `apps/api/tests/unit/mcp/test_email_connector.py`
- [ ] Handles rate limits and retries gracefully

## Getting Started

1. Fork and clone the repository
2. Review `apps/api/mcp/base.py` for the ABC interface
3. Review `apps/api/mcp/connectors/web_scraper.py` as reference
4. Create branch: `git checkout -b feature/email-mcp-connector`
5. Implement, test, and open a PR against `dev`

## Questions?

Comment on this issue and a maintainer will help you get started.
