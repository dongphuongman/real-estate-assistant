# ADR-0009: Project License — MIT

## Status

Accepted (2026-03-28)

## Context

The PRD V4 specified "License: AGPLv3" for the Community Edition, but the actual codebase has been MIT-licensed from the start:

- `LICENSE` file contains MIT text
- `package.json` (root) has `"license": "MIT"`
- `apps/api/pyproject.toml` has `license = {text = "MIT"}`
- `README.md` displays an MIT badge

This created a discrepancy between documentation (PRD) and the actual codebase. A decision was needed: switch to AGPLv3 (as PRD stated) or reconcile to MIT (matching the codebase reality).

## Decision

**Keep MIT as the project license.** Update all documentation to reflect MIT consistently.

### Rationale

1. **Honesty to existing codebase** — All files already declare MIT; switching to AGPLv3 would be retroactive and could confuse contributors.
2. **Simplicity** — MIT is permissive, well-understood, and reduces friction for adoption and contribution.
3. **Sponsor-friendliness** — MIT is simpler for future sponsors and commercial users to work with.
4. **No dependency conflict** — AGENTS.md already restricts GPL/AGPL *dependencies*, which is orthogonal to the project's own license.

### Changes Made

- `docs/process/PRD.MD`: Updated `License: AGPLv3` → `License: MIT`
- `AGENTS.md`: Clarified GPL constraint applies to dependencies only, not the project license
- `apps/web/package.json`: Added missing `"license": "MIT"` field
- `docs/development/CONTRIBUTING.md`: Added license section
- This ADR documents the decision

## Consequences

**Positive:**
- Consistent license across all files and documentation
- No contributor confusion about licensing terms
- Permissive license encourages adoption and contribution

**Negative:**
- No copyleft protection (anyone can use code in closed-source projects)
- Less alignment with "Open Core" strategy where CE might benefit from copyleft

## Alternatives Considered

1. **AGPLv3** (as originally specified in PRD V4): Would provide copyleft protection and align with Open Core model, but conflicts with existing MIT declarations and adds contributor friction.
2. **Apache 2.0**: Similar permissiveness with patent grants, but no patent concerns in current scope.
3. **Dual licensing (MIT + AGPLv3)**: Adds complexity without clear benefit for a solo-developer project at this stage.
