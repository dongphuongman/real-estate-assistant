from __future__ import annotations

import subprocess
import sys


def test_dev_start_script_dry_run_does_not_print_secrets() -> None:
    result = subprocess.run(
        [sys.executable, "scripts/dev/start.py", "--mode", "local", "--dry-run"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    out = result.stdout
    assert "BACKEND_CMD:" in out
    assert "FRONTEND_CMD:" in out
    assert "dev-secret-key" not in out
    assert "<redacted>" in out

