#!/usr/bin/env bash
# Run ALL tests and see complete picture of failures
#
# Runs all CI tests without stopping on first failure.
# Perfect for preparing fixes - you'll see all issues at once.
#
# This is equivalent to: run_ci_tests_local.sh --continue-on-error

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "Running ALL tests (will not stop on failures)..."
echo "This will show you the complete picture of all issues."
echo ""

"$SCRIPT_DIR/run_ci_tests_local.sh" --continue-on-error
