# Agent Rules (Trae)

## Rules
- **Flow**: Zero clarification. Win paths. English.
- **Format**: Full paths (Rule 7). DD.MM.YYYY.
- **Role**: Proactive. Fix lint. Use **Context7 MCP**.

## Skills
- **Nav**: Search first. Read context. Use `#Web`/`#Doc`.
- **Edit**: Incremental. Check deps. `pytest`/`ruff`/`mypy`.
- **Tools**: `@Agent`, `TodoWrite`, `manage_core_memory`.
- **Local**: See `.trae/skills/` (`codemap`, `python-dev`, `frontend`, `test`, `docker`).

## Playbooks
- **Gen**: Plan>Search>Ctx>Edit>Verify>Report.
- **Fix**: Repro>Test>Fix>Verify.
- **Feat**: API>Test>Impl.
- **UI**: Logic in Svc. No brittle tests.

## System
- **Auto**: `DevPipeline` (`workflows/pipeline.py`).
- **Agents**: Code, Debug, Test, Doc.
- **Check**: `RuleEngine`.
