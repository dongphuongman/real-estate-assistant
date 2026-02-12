#!/bin/bash
# Convenience script for running the AI Real Estate Assistant locally
# This is a wrapper around the launcher script with sensible defaults

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

echo "Starting AI Real Estate Assistant..."
echo "Project root: $PROJECT_ROOT"

# Check if Python is available
if ! command -v python &> /dev/null; then
    echo "Error: Python is not installed or not on PATH."
    echo "Please install Python 3.11+ from https://python.org"
    exit 1
fi

# Run the launcher script with sensible defaults
python "$PROJECT_ROOT/scripts/launcher/start.py" "$@"
