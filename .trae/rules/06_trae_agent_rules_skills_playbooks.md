# Agent Rules & Skills (Trae Rules)

## Rules
- **Workflow**: Zero clarification (act on assumptions). Windows paths.
- **Output**: Full relative paths. DD.MM.YYYY dates. English code/docs.
- **Role**: Proactive senior pair-programmer. Fix lint errors.

## Skills
- **Navigation**: Search concepts first. Read context before editing.
- **Implementation**: Incremental changes. No new deps without check.
- **Verification**: Run `pytest`, `ruff`, `mypy`.
- **Task Management**: Use `TodoWrite` for complex tasks.
- **Memory**: Use `manage_core_memory` to persist knowledge.
- **Reporting**: Link to files. Summarize changes.

## Playbooks
- **Default**: Plan -> Search -> Read -> Edit -> Test -> Lint -> Format -> Type Check -> Summarize.
- **Bug Fix**: Reproduce -> Fail Test -> Fix -> Verify.
- **New Feature**: Interface -> Tests -> Implementation -> Verify.
- **UI**: Logic in service layer. Avoid brittle UI tests.

## Internal Agent System
- Use `workflows/pipeline.py` (`DevPipeline`) for automated tasks.
- Agents: Coding, Debugging, Testing, Documentation.
- Check generated code with `RuleEngine`.
