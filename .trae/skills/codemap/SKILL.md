name: codemap
description: Analyze codebase structure, dependencies, and changes. Use when user asks about project structure, where code is located, how files connect, what changed, or before starting any coding task. Provides instant architectural context.
---

# Codemap
Codemap gives you instant architectural context about any codebase. Use it proactively before exploring or modifying code.

## Commands
- **Discovery**: Use `ls -R` (recursive list) to map the directory structure.
- **Dependencies**: Read `pyproject.toml`, `requirements.txt`, or `package.json`.
- **Entry Points**: Look for `main.py`, `app.py`, `wsgi.py`, or `manage.py`.
- **Search**: Use `SearchCodebase` with high-level terms (e.g., "auth", "database", "api") to find core modules.

## When to Use
- User asks "What does this project do?"
- User asks "Where is X implemented?"
- Before starting a complex task to understand impact.
- To identify "hub" files (files imported by many others).

## Output Interpretation
- **Structure**: Directories and key files.
- **Dependencies**: Key libraries and their purpose.
- **Flow**: How data/control flows through the app.

## Examples
**User**: "Explain the project structure."
**Agent**: 
1. Runs `ls -R` to get the tree.
2. Reads config files.
3. Summarizes: "The project is a Django app with `core` and `api` apps. Key dependencies are..."
