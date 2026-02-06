from __future__ import annotations

from pathlib import Path

from scripts.security.forbidden_tokens_check import main as forbidden_tokens_main


def test_no_forbidden_tokens_in_repo() -> None:
    project_root = Path(__file__).resolve().parents[2]
    assert forbidden_tokens_main(["--root", str(project_root)]) == 0
