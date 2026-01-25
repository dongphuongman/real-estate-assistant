import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path


def _project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _run_checked(cmd: list[str], cwd: Path, env: dict[str, str] | None = None) -> None:
    subprocess.run(cmd, cwd=str(cwd), check=True, env=env)


def _has_docker_compose() -> bool:
    if shutil.which("docker") is None:
        return False
    try:
        subprocess.run(["docker", "compose", "version"], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True
    except Exception:
        return False


def _ensure_uv_dev_env(root: Path) -> None:
    _run_checked([sys.executable, str(root / "scripts" / "dev" / "bootstrap_uv.py"), "--dev"], cwd=root)


def _run_docker(root: Path) -> int:
    if not _has_docker_compose():
        print("Docker Compose is not available. Run with --mode local.", file=sys.stderr)
        return 2
    subprocess.run(["docker", "compose", "up", "--build"], cwd=str(root))
    return 0


def _run_local(root: Path) -> int:
    if shutil.which("npm") is None:
        print("npm is not installed or not on PATH.", file=sys.stderr)
        return 2

    _ensure_uv_dev_env(root)

    env_backend = os.environ.copy()
    env_backend.setdefault("ENVIRONMENT", "development")
    env_backend.setdefault("API_ACCESS_KEY", "dev-secret-key")

    env_frontend = os.environ.copy()
    env_frontend.setdefault("NEXT_PUBLIC_API_URL", "/api/v1")
    env_frontend.setdefault("BACKEND_API_URL", "http://localhost:8000/api/v1")
    env_frontend.setdefault("API_ACCESS_KEY", env_backend.get("API_ACCESS_KEY", "dev-secret-key"))

    backend = subprocess.Popen(
        ["uv", "run", "uvicorn", "api.main:app", "--reload", "--host", "0.0.0.0", "--port", "8000"],
        cwd=str(root),
        env=env_backend,
    )
    frontend = subprocess.Popen(
        ["npm", "run", "dev"],
        cwd=str(root / "frontend"),
        env=env_frontend,
    )

    procs = [backend, frontend]
    try:
        while True:
            for proc in procs:
                code = proc.poll()
                if code is not None:
                    for other in procs:
                        if other is not proc and other.poll() is None:
                            other.terminate()
                    return code
    except KeyboardInterrupt:
        for proc in procs:
            if proc.poll() is None:
                proc.terminate()
        return 130


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["auto", "docker", "local"], default="auto")
    args = parser.parse_args()

    root = _project_root()

    if args.mode == "auto":
        return _run_docker(root) if _has_docker_compose() else _run_local(root)
    if args.mode == "docker":
        return _run_docker(root)
    return _run_local(root)


if __name__ == "__main__":
    raise SystemExit(main())
