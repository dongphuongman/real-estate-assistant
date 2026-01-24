from __future__ import annotations

from pathlib import Path

import pytest

from scripts.forbidden_tokens_check import main as forbidden_tokens_main


def test_forbidden_tokens_check_passes_when_no_tokens_present(tmp_path: Path) -> None:
    (tmp_path / "a.txt").write_text("hello\nworld\n", encoding="utf-8")
    assert forbidden_tokens_main(["--root", str(tmp_path)]) == 0


def test_forbidden_tokens_check_fails_when_token_present(tmp_path: Path) -> None:
    (tmp_path / "b.txt").write_text("x=NEXT_PUBLIC_API_KEY\n", encoding="utf-8")
    with pytest.raises(SystemExit):
        forbidden_tokens_main(["--root", str(tmp_path)])


def test_forbidden_tokens_check_ignores_node_modules(tmp_path: Path) -> None:
    node_modules = tmp_path / "node_modules"
    node_modules.mkdir(parents=True)
    (node_modules / "c.txt").write_text("NEXT_PUBLIC_API_KEY\n", encoding="utf-8")
    assert forbidden_tokens_main(["--root", str(tmp_path)]) == 0
