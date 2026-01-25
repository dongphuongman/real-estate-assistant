from __future__ import annotations

import subprocess
import sys


def test_ci_parity_script_dry_run_prints_expected_steps() -> None:
    result = subprocess.run(
        [sys.executable, "scripts/ci_parity.py", "--dry-run"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    out = result.stdout
    assert "RUN:" in out
    assert "ruff check" in out
    assert "mypy" in out
    assert "bandit" in out
    assert "pip_audit" in out
    assert "pytest" in out
    assert "coverage_gate.py" in out
