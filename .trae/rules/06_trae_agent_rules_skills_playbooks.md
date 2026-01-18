# Agent Rules & Skills (Trae Rules)

## Rules
- **Workflow**: Zero clarification. Windows paths.
- **Output**: Rule 7 (Full paths). DD.MM.YYYY. English.
- **Role**: Proactive pair-programmer. Fix lint.
- **Docs**: Always use **Context7 MCP** for library/API docs & code gen.

## Skills
- **Navigation**: Search concepts first. Read context before editing.
- **Context**: Use `#Web` (online), `#Doc` (files/specs). Manage `.trae/.ignore`.
- **Implementation**: Incremental changes. No new deps without check.
- **Verification**: Run `pytest`, `ruff`, `mypy`.
- **Agents**: Use `@Agent` for specialized tasks. Max Mode for deep coding.
- **Task & Memory**: `TodoWrite` for plans. `manage_core_memory` for knowledge.
- **Local Skills**: Check `.trae/skills/` for `codemap` and `python-development`.

## Playbooks
- **General**: Plan -> Search -> Context -> Edit -> Verify -> Report.
- **Fix**: Reproduce -> Test -> Fix -> Verify.
- **Feat**: Interface -> Tests -> Impl.
- **UI**: Service logic. Avoid brittle tests.

## Internal Agent System
- **Auto**: `workflows/pipeline.py` (`DevPipeline`).
- **Agents**: Coding, Debugging, Testing, Documentation.
- **Check**: Verify with `RuleEngine`.
