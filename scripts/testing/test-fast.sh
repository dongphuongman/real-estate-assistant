#!/usr/bin/env bash
# Quick test run for rapid feedback during development
#
# Runs tests in fast mode:
# - Skips slow tests
# - Skips mypy type checking
# - Parallel execution enabled
# - No coverage reports
#
# Perfect for quick validation during active development.
#
# This is equivalent to: run_ci_tests_local.sh --fast

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "Running tests in FAST mode..."
echo "Skipping slow tests and type checking for quick feedback."
echo ""

"$SCRIPT_DIR/run_ci_tests_local.sh" --fast
