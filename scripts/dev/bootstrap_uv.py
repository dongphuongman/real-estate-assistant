import argparse
import shutil
import subprocess
import sys
from pathlib import Path


def _project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _run(cmd: list[str], cwd: Path) -> None:
    subprocess.run(cmd, cwd=str(cwd), check=True)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dev", action="store_true", help="Install dev dependencies as well.")
    args = parser.parse_args()

    root = _project_root()

    if shutil.which("uv") is None:
        print("uv is not installed or not on PATH.", file=sys.stderr)
        print("See docs/scripts/LOCAL_DEVELOPMENT.md for installation options.", file=sys.stderr)
        return 2

    venv_dir = root / ".venv"
    if not venv_dir.exists():
        _run(["uv", "venv", str(venv_dir)], cwd=root)

    extras = ".[dev]" if args.dev else "."
    _run(["uv", "pip", "install", "-e", extras], cwd=root)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
