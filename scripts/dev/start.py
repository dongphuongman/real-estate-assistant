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
        subprocess.run(
            ["docker", "compose", "version"],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return True
    except Exception:
        return False


def _get_default_api_access_key_from_env() -> str:
    raw = os.environ.get("API_ACCESS_KEY", "").strip()
    if raw:
        return raw
    rotated = os.environ.get("API_ACCESS_KEYS", "")
    if not rotated:
        return ""
    first = next((v.strip() for v in rotated.split(",") if v.strip()), "")
    return first


def _ensure_uv_dev_env(root: Path) -> None:
    _run_checked(
        [sys.executable, str(root / "scripts" / "dev" / "bootstrap_uv.py"), "--dev"], cwd=root
    )


def _docker_gpu_available() -> bool:
    if shutil.which("docker") is None:
        return False
    try:
        subprocess.run(
            ["docker", "run", "--rm", "--gpus", "all", "alpine:3.20", "true"],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return True
    except Exception:
        return False


def _choose_docker_mode_interactively(*, default_mode: str) -> str:
    if not sys.stdin or not sys.stdin.isatty():
        return default_mode
    print("Select Docker mode:")
    print("  1) auto (GPU if available, else CPU)")
    print("  2) cpu")
    print("  3) gpu")
    raw = input(f"Choice [default: {default_mode}]: ").strip()
    if not raw:
        return default_mode
    if raw == "1":
        return "auto"
    if raw == "2":
        return "cpu"
    if raw == "3":
        return "gpu"
    if raw.lower() in {"auto", "cpu", "gpu"}:
        return raw.lower()
    return default_mode


def _run_docker(root: Path, *, profiles: list[str]) -> int:
    if not _has_docker_compose():
        print("Docker Compose is not available. Run with --mode local.", file=sys.stderr)
        return 2
    env = os.environ.copy()
    if "gpu" in profiles:
        env.setdefault("OLLAMA_API_BASE", "http://ollama-gpu:11434")
        env.setdefault("OLLAMA_HOST", "http://ollama-gpu:11434")
    if "internet" in profiles:
        env.setdefault("INTERNET_ENABLED", "true")
    cmd = ["docker", "compose"]
    for profile in profiles:
        cmd.extend(["--profile", profile])
    cmd.extend(["up", "--build"])
    subprocess.run(cmd, cwd=str(root), env=env)
    return 0


def _sanitize_env_for_display(env: dict[str, str]) -> dict[str, str]:
    redacted_markers = ("KEY", "TOKEN", "SECRET", "PASSWORD")
    safe: dict[str, str] = {}
    for k, v in env.items():
        if any(marker in k.upper() for marker in redacted_markers):
            safe[k] = "<redacted>"
        else:
            safe[k] = v
    return safe


def _build_backend_env() -> dict[str, str]:
    env = os.environ.copy()
    env.setdefault("ENVIRONMENT", "development")
    if not env.get("API_ACCESS_KEY", "").strip() and not env.get("API_ACCESS_KEYS", "").strip():
        env["API_ACCESS_KEY"] = "dev-secret-key"
    return env


def _build_frontend_env(*, backend_env: dict[str, str]) -> dict[str, str]:
    env = os.environ.copy()
    env.setdefault("NEXT_PUBLIC_API_URL", "/api/v1")
    env.setdefault("BACKEND_API_URL", "http://localhost:8000/api/v1")
    if not env.get("API_ACCESS_KEY", "").strip() and not env.get("API_ACCESS_KEYS", "").strip():
        effective_backend_key = (
            backend_env.get("API_ACCESS_KEY", "").strip() or _get_default_api_access_key_from_env()
        )
        if effective_backend_key:
            env["API_ACCESS_KEY"] = effective_backend_key
    return env


def _run_local(root: Path, *, service: str, no_bootstrap: bool, dry_run: bool) -> int:
    wants_backend = service in {"all", "backend"}
    wants_frontend = service in {"all", "frontend"}

    backend_cmd = [
        "uv",
        "run",
        "uvicorn",
        "api.main:app",
        "--reload",
        "--host",
        "0.0.0.0",
        "--port",
        "8000",
    ]
    frontend_cmd = ["npm", "run", "dev"]

    env_backend = _build_backend_env()
    env_frontend = _build_frontend_env(backend_env=env_backend)

    if dry_run:
        if wants_backend:
            print("BACKEND_CMD:", " ".join(backend_cmd))
        if wants_frontend:
            print("FRONTEND_CMD:", " ".join(frontend_cmd))
        if wants_backend:
            print(
                "BACKEND_ENV:",
                _sanitize_env_for_display(
                    {
                        k: env_backend[k]
                        for k in sorted(env_backend)
                        if k in {"ENVIRONMENT", "API_ACCESS_KEY", "API_ACCESS_KEYS"}
                    }
                ),
            )
        if wants_frontend:
            keys = {"NEXT_PUBLIC_API_URL", "BACKEND_API_URL", "API_ACCESS_KEY", "API_ACCESS_KEYS"}
            print(
                "FRONTEND_ENV:",
                _sanitize_env_for_display(
                    {k: env_frontend[k] for k in sorted(env_frontend) if k in keys}
                ),
            )
        return 0

    if wants_frontend and shutil.which("npm") is None:
        print("npm is not installed or not on PATH.", file=sys.stderr)
        return 2

    if wants_backend:
        if shutil.which("uv") is None:
            print("uv is not installed or not on PATH.", file=sys.stderr)
            return 2
        if not no_bootstrap:
            _ensure_uv_dev_env(root)

    procs: list[subprocess.Popen[bytes]] = []
    try:
        if wants_backend:
            procs.append(subprocess.Popen(backend_cmd, cwd=str(root), env=env_backend))
        if wants_frontend:
            procs.append(
                subprocess.Popen(frontend_cmd, cwd=str(root / "frontend"), env=env_frontend)
            )

        while True:
            for proc in procs:
                code = proc.poll()
                if code is not None:
                    for other in procs:
                        if other is not proc and other.poll() is None:
                            other.terminate()
                    return int(code)
    except KeyboardInterrupt:
        for proc in procs:
            if proc.poll() is None:
                proc.terminate()
        return 130


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["auto", "docker", "local"], default="auto")
    parser.add_argument("--service", choices=["all", "backend", "frontend"], default="all")
    parser.add_argument("--docker-mode", choices=["auto", "cpu", "gpu", "ask"], default="auto")
    parser.add_argument("--docker-profile", action="append", default=[])
    parser.add_argument("--internet", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--no-bootstrap", action="store_true")
    args = parser.parse_args(argv)
    if bool(args.internet):
        os.environ.setdefault("INTERNET_ENABLED", "true")

    root = _project_root()
    docker_mode = str(args.docker_mode)
    if docker_mode == "ask":
        docker_mode = _choose_docker_mode_interactively(default_mode="auto")

    requested_profiles = [p for p in args.docker_profile if p and p.strip()]
    effective_profiles = list(requested_profiles)
    if bool(args.internet) and "internet" not in effective_profiles:
        effective_profiles.append("internet")
    if docker_mode == "gpu":
        if "gpu" not in effective_profiles:
            effective_profiles.append("gpu")
    elif docker_mode == "auto":
        if "gpu" not in effective_profiles and _docker_gpu_available():
            effective_profiles.append("gpu")

    if args.mode == "auto":
        if _has_docker_compose():
            if args.dry_run:
                prefix = "docker compose"
                profiles = " ".join(f"--profile {p}" for p in effective_profiles)
                cmd = f"{prefix} {profiles} up --build".strip()
                cmd = " ".join(cmd.split())
                print(f"DOCKER_CMD: {cmd}")
                return 0
            return _run_docker(root, profiles=effective_profiles)
        return _run_local(
            root,
            service=args.service,
            no_bootstrap=bool(args.no_bootstrap),
            dry_run=bool(args.dry_run),
        )
    if args.mode == "docker":
        if args.dry_run:
            prefix = "docker compose"
            profiles = " ".join(f"--profile {p}" for p in effective_profiles)
            cmd = f"{prefix} {profiles} up --build".strip()
            cmd = " ".join(cmd.split())
            print(f"DOCKER_CMD: {cmd}")
            return 0
        return _run_docker(root, profiles=effective_profiles)
    return _run_local(
        root, service=args.service, no_bootstrap=bool(args.no_bootstrap), dry_run=bool(args.dry_run)
    )


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
