from __future__ import annotations

import argparse
import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class TokenMatch:
    relative_path: str
    line_number: int
    token: str


def _is_probably_binary(prefix: bytes) -> bool:
    return b"\x00" in prefix


def _scan_file_for_tokens(
    file_path: Path,
    relative_path: str,
    tokens: list[str],
    *,
    max_bytes: int,
) -> list[TokenMatch]:
    try:
        with file_path.open("rb") as f:
            prefix = f.read(4096)
            if _is_probably_binary(prefix):
                return []
            content = prefix + f.read(max_bytes - len(prefix) if max_bytes > len(prefix) else 0)
    except OSError:
        return []

    text = content.decode("utf-8", errors="replace")
    matches: list[TokenMatch] = []
    for idx, line in enumerate(text.splitlines(), start=1):
        for token in tokens:
            if token in line:
                matches.append(
                    TokenMatch(relative_path=relative_path, line_number=idx, token=token)
                )
    return matches


def main(argv: list[str] | None = None) -> int:
    project_root = Path(__file__).resolve().parents[1]

    parser = argparse.ArgumentParser(
        description="Fail if any forbidden tokens appear in the repository.",
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=project_root,
        help="Repository root to scan (default: project root).",
    )
    parser.add_argument(
        "--token",
        action="append",
        default=["NEXT_PUBLIC_API_KEY"],
        help="Forbidden token to search for. Repeatable. Default: NEXT_PUBLIC_API_KEY",
    )
    parser.add_argument(
        "--max-bytes",
        type=int,
        default=2_000_000,
        help="Max bytes to read per file (default: 2000000).",
    )
    args = parser.parse_args(argv)

    root = args.root.resolve()
    tokens = [t for t in args.token if t]
    ignore_dir_names = {
        ".git",
        ".history",
        ".venv",
        "node_modules",
        ".pytest_cache",
        ".mypy_cache",
        ".ruff_cache",
        ".next",
        "dist",
        "build",
        "coverage",
    }
    ignore_paths = {
        "docs/openapi.json",
        "frontend/package-lock.json",
        "scripts/forbidden_tokens_check.py",
        "tests/unit/test_forbidden_tokens_check.py",
    }

    all_matches: list[TokenMatch] = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in ignore_dir_names]
        for filename in filenames:
            file_path = Path(dirpath) / filename
            try:
                rel = file_path.relative_to(root).as_posix()
            except ValueError:
                rel = str(file_path)

            if rel in ignore_paths:
                continue

            matches = _scan_file_for_tokens(
                file_path=file_path,
                relative_path=rel,
                tokens=tokens,
                max_bytes=args.max_bytes,
            )
            all_matches.extend(matches)

    if all_matches:
        all_matches_sorted = sorted(
            all_matches, key=lambda m: (m.relative_path, m.line_number, m.token)
        )
        details = "\n".join(
            f"- {m.relative_path}:{m.line_number} ({m.token})" for m in all_matches_sorted[:200]
        )
        raise SystemExit(
            "Forbidden tokens detected:\n"
            f"{details}\n\n"
            "Remove the token(s) from the repository or move them to server-only env variables."
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
