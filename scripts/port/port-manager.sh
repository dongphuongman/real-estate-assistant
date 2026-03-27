#!/bin/bash
# Port Manager - Cross-platform port management wrapper
# Usage: ./port-manager.sh --action allocate --category backend

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$(dirname "$(dirname "$SCRIPT_DIR")")" && pwd)"

# Find Python
PYTHON=""
if command -v python3 &> /dev/null; then
    PYTHON="python3"
elif command -v python &> /dev/null; then
    PYTHON="python"
else
    echo "Error: Python not found. Please install Python 3.8+ and ensure it's on PATH."
    exit 1
fi

# Execute port manager
exec "$PYTHON" "$SCRIPT_DIR/port-manager.py" --project-root "$PROJECT_ROOT" "$@"
