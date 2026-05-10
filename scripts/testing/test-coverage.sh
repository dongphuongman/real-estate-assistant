#!/usr/bin/env bash
# Run tests with coverage reports
#
# Runs all CI tests with code coverage analysis.
# Generates coverage.xml and terminal coverage report.
#
# Use this before committing to ensure adequate test coverage.
#
# This is equivalent to: run_ci_tests_local.sh --coverage

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "Running tests with COVERAGE analysis..."
echo "This will generate coverage.xml report."
echo ""

"$SCRIPT_DIR/run_ci_tests_local.sh" --coverage
