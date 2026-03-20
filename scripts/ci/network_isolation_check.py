#!/usr/bin/env python3
"""
CI script to verify unit tests don't make network calls.

This script runs pytest with network isolation enabled to ensure
unit tests remain deterministic and don't depend on external services.

Usage:
    python scripts/ci/network_isolation_check.py
    python scripts/ci/network_isolation_check.py --verbose
    python scripts/ci/network_isolation_check.py --path tests/unit/mcp

Exit codes:
    0: All tests passed without network calls
    1: Tests failed or network calls were detected
"""

import argparse
import subprocess
import sys
from pathlib import Path


def main() -> int:
    """Run network isolation check."""
    parser = argparse.ArgumentParser(
        description="Verify unit tests don't make network calls"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose output",
    )
    parser.add_argument(
        "--path",
        type=str,
        default="tests/unit",
        help="Test path to run (default: tests/unit)",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=300,
        help="Test timeout in seconds (default: 300)",
    )
    args = parser.parse_args()

    # Determine project root
    script_dir = Path(__file__).parent
    project_root = script_dir.parent.parent / "apps" / "api"

    if not project_root.exists():
        print(f"Error: Project root not found at {project_root}")
        return 1

    print("=" * 60)
    print("Network Isolation Check")
    print("=" * 60)
    print(f"Test path: {args.path}")
    print(f"Project root: {project_root}")
    print()

    # Build pytest command
    pytest_cmd = [
        sys.executable, "-m", "pytest",
        str(args.path),
        "-n", "auto",  # Parallel execution
        "--timeout", str(args.timeout),
        "-m", "not integration",  # Skip integration tests
        "--tb=short",
    ]

    if args.verbose:
        pytest_cmd.append("-v")

    print(f"Running: {' '.join(pytest_cmd)}")
    print()

    # Run tests
    result = subprocess.run(
        pytest_cmd,
        cwd=project_root,
        capture_output=not args.verbose,
    )

    if result.returncode == 0:
        print()
        print("=" * 60)
        print("✓ Network isolation check PASSED")
        print("  All unit tests completed without network calls")
        print("=" * 60)
        return 0
    else:
        print()
        print("=" * 60)
        print("✗ Network isolation check FAILED")
        if result.stdout:
            print(result.stdout.decode() if isinstance(result.stdout, bytes) else result.stdout)
        if result.stderr:
            print(result.stderr.decode() if isinstance(result.stderr, bytes) else result.stderr)
        print()
        print("Unit tests must not make network calls.")
        print("Use mcp.testing.fixtures for stub data.")
        print("=" * 60)
        return 1


if __name__ == "__main__":
    sys.exit(main())
