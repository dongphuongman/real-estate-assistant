#!/usr/bin/env bash
# Run full CI test suite (exactly as CI does)
#
# Runs the complete CI test suite with all checks:
# - Linting (ruff)
# - RuleEngine test
# - Security scans
# - OpenAPI diff
# - Alembic migrations
# - Unit tests (parallel)
# - Integration tests (parallel)
# - Type checking (mypy)
#
# Use this before pushing to ensure CI will pass.
#
# This is the default mode: run_ci_tests_local.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "Running FULL CI test suite..."
echo "This replicates exactly what GitHub Actions will run."
echo ""

"$SCRIPT_DIR/run_ci_tests_local.sh"
