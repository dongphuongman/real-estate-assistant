from __future__ import annotations

import argparse
import subprocess
import sys
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Callable


@dataclass(frozen=True)
class SmokeConfig:
    compose_file: Path
    backend_health_url: str
    frontend_url: str
    timeout_seconds: int
    interval_seconds: float
    build: bool
    down: bool
    dry_run: bool


def build_compose_base_command(compose_file: Path) -> list[str]:
    return ["docker", "compose", "-f", str(compose_file)]


def build_compose_up_command(base: list[str], *, build: bool) -> list[str]:
    cmd = [*base, "up", "-d"]
    if build:
        cmd.append("--build")
    return cmd


def build_compose_down_command(base: list[str]) -> list[str]:
    return [*base, "down", "--volumes", "--remove-orphans"]


def run_command(cmd: list[str]) -> None:
    subprocess.run(cmd, check=True)


def http_get_status(url: str, *, timeout_seconds: float) -> int:
    req = urllib.request.Request(url, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=timeout_seconds) as resp:
            return int(resp.status)
    except urllib.error.HTTPError as exc:
        return int(exc.code)


def wait_for_http_ok(
    url: str,
    *,
    timeout_seconds: int,
    interval_seconds: float,
    get_status: Callable[[str, float], int],
    sleep: Callable[[float], None],
) -> None:
    deadline = time.monotonic() + timeout_seconds
    last_status: int | None = None
    while time.monotonic() < deadline:
        try:
            last_status = get_status(url, 2.0)
            if 200 <= last_status < 300:
                return
        except OSError:
            last_status = None
        sleep(interval_seconds)

    status_part = "unknown" if last_status is None else str(last_status)
    raise TimeoutError(f"Timed out waiting for {url} (last_status={status_part})")


def parse_args(argv: list[str]) -> SmokeConfig:
    parser = argparse.ArgumentParser(description="Docker Compose smoke test (backend + frontend).")
    parser.add_argument("--compose-file", default="docker-compose.yml")
    parser.add_argument("--backend-health-url", default="http://localhost:8000/health")
    parser.add_argument("--frontend-url", default="http://localhost:3000/")
    parser.add_argument("--timeout-seconds", type=int, default=180)
    parser.add_argument("--interval-seconds", type=float, default=2.0)
    parser.add_argument("--build", action="store_true")
    parser.add_argument("--down", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--ci", action="store_true", help="CI defaults: build+down, longer timeout.")

    ns = parser.parse_args(argv)
    build = bool(ns.build)
    down = bool(ns.down)
    timeout_seconds = int(ns.timeout_seconds)

    if ns.ci:
        build = True
        down = True
        timeout_seconds = max(timeout_seconds, 240)

    return SmokeConfig(
        compose_file=Path(ns.compose_file),
        backend_health_url=str(ns.backend_health_url),
        frontend_url=str(ns.frontend_url),
        timeout_seconds=timeout_seconds,
        interval_seconds=float(ns.interval_seconds),
        build=build,
        down=down,
        dry_run=bool(ns.dry_run),
    )


def main(argv: list[str]) -> int:
    cfg = parse_args(argv)
    compose_file = cfg.compose_file.resolve()

    if not compose_file.exists():
        raise FileNotFoundError(f"Compose file not found: {compose_file}")

    base = build_compose_base_command(compose_file)
    up_cmd = build_compose_up_command(base, build=cfg.build)
    down_cmd = build_compose_down_command(base)

    if cfg.dry_run:
        print("UP:", " ".join(up_cmd))
        print("DOWN:", " ".join(down_cmd))
        print("CHECK:", cfg.backend_health_url)
        print("CHECK:", cfg.frontend_url)
        return 0

    try:
        run_command(up_cmd)
        wait_for_http_ok(
            cfg.backend_health_url,
            timeout_seconds=cfg.timeout_seconds,
            interval_seconds=cfg.interval_seconds,
            get_status=http_get_status,
            sleep=time.sleep,
        )
        wait_for_http_ok(
            cfg.frontend_url,
            timeout_seconds=cfg.timeout_seconds,
            interval_seconds=cfg.interval_seconds,
            get_status=http_get_status,
            sleep=time.sleep,
        )
        return 0
    finally:
        if cfg.down:
            run_command(down_cmd)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

