from __future__ import annotations

import argparse
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence


@dataclass(frozen=True)
class ParityConfig:
    python_exe: str
    base_ref: str | None
    run_unit: bool
    run_integration: bool
    dry_run: bool


def build_ruff_check_cmd(python_exe: str) -> list[str]:
    return [python_exe, "-m", "ruff", "check", "."]


def build_mypy_cmd(python_exe: str) -> list[str]:
    return [python_exe, "-m", "mypy"]


def build_rule_engine_check_cmd(python_exe: str) -> list[str]:
    return [python_exe, "-m", "pytest", "-q", "tests/integration/test_rule_engine_clean.py"]


def build_forbidden_tokens_cmd(python_exe: str) -> list[str]:
    return [python_exe, "scripts/forbidden_tokens_check.py"]


def build_openapi_drift_cmd(python_exe: str) -> list[str]:
    return [python_exe, "scripts/export_openapi.py", "--check"]


def build_api_reference_generated_drift_cmd(python_exe: str) -> list[str]:
    return [python_exe, "scripts/generate_api_reference.py", "--check"]


def build_api_reference_full_drift_cmd(python_exe: str) -> list[str]:
    return [python_exe, "scripts/update_api_reference_full.py", "--check"]


def build_bandit_cmd(python_exe: str) -> list[str]:
    targets = [
        "api",
        "agents",
        "ai",
        "analytics",
        "config",
        "data",
        "i18n",
        "models",
        "notifications",
        "rules",
        "scripts",
        "tools",
        "utils",
        "vector_store",
        "workflows",
    ]
    existing_targets = [target for target in targets if Path(target).exists()]
    return [
        python_exe,
        "-m",
        "bandit",
        "-r",
        *existing_targets,
        "-lll",
        "-iii",
    ]


def build_pip_audit_cmd(python_exe: str) -> list[str]:
    return [
        python_exe,
        "-m",
        "pip_audit",
        "-r",
        "requirements.txt",
        "--ignore-vuln",
        "GHSA-7gcm-g887-7qv7",
        "--ignore-vuln",
        "CVE-2026-0994",
    ]


def build_unit_tests_cmd(python_exe: str) -> list[str]:
    return [
        python_exe,
        "-m",
        "pytest",
        "tests/unit",
        "--cov=.",
        "--cov-report=xml",
        "--cov-report=term",
        "-n",
        "auto",
    ]


def build_integration_tests_cmd(python_exe: str) -> list[str]:
    return [
        python_exe,
        "-m",
        "pytest",
        "tests/integration",
        "--cov=.",
        "--cov-report=xml",
        "--cov-report=term",
    ]


def build_unit_diff_coverage_gate_cmd(python_exe: str, *, base_ref: str | None) -> list[str]:
    cmd = [
        python_exe,
        "scripts/coverage_gate.py",
        "diff",
        "--coverage-xml",
        "coverage.xml",
        "--min-coverage",
        "90",
        "--exclude",
        "tests/*",
        "--exclude",
        "scripts/*",
        "--exclude",
        "workflows/*",
    ]
    if base_ref:
        cmd.extend(["--base-ref", base_ref])
    return cmd


def build_unit_critical_coverage_gate_cmd(python_exe: str) -> list[str]:
    return [
        python_exe,
        "scripts/coverage_gate.py",
        "critical",
        "--coverage-xml",
        "coverage.xml",
        "--min-coverage",
        "90",
        "--include",
        "api/*.py",
        "--include",
        "api/routers/*.py",
        "--include",
        "rules/*.py",
        "--include",
        "models/provider_factory.py",
        "--include",
        "models/user_model_preferences.py",
        "--include",
        "config/*.py",
    ]


def build_integration_diff_coverage_gate_cmd(python_exe: str, *, base_ref: str | None) -> list[str]:
    cmd = [
        python_exe,
        "scripts/coverage_gate.py",
        "diff",
        "--coverage-xml",
        "coverage.xml",
        "--min-coverage",
        "70",
        "--exclude",
        "tests/*",
        "--exclude",
        "scripts/*",
        "--exclude",
        "workflows/*",
    ]
    if base_ref:
        cmd.extend(["--base-ref", base_ref])
    return cmd


def format_command(cmd: Sequence[str]) -> str:
    return subprocess.list2cmdline(list(cmd))


def run_command(cmd: Sequence[str]) -> None:
    subprocess.run(list(cmd), check=True)


def parse_args(argv: Sequence[str]) -> ParityConfig:
    parser = argparse.ArgumentParser(description="Run CI-parity backend quality gates locally.")
    parser.add_argument("--python", default=sys.executable)
    parser.add_argument("--base-ref", default=None)
    parser.add_argument("--unit-only", action="store_true")
    parser.add_argument("--integration-only", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    ns = parser.parse_args(list(argv))

    run_unit = True
    run_integration = True
    if ns.unit_only:
        run_integration = False
    if ns.integration_only:
        run_unit = False

    return ParityConfig(
        python_exe=str(ns.python),
        base_ref=str(ns.base_ref) if ns.base_ref is not None else None,
        run_unit=run_unit,
        run_integration=run_integration,
        dry_run=bool(ns.dry_run),
    )


def build_commands(cfg: ParityConfig) -> list[list[str]]:
    cmds: list[list[str]] = [
        build_ruff_check_cmd(cfg.python_exe),
        build_mypy_cmd(cfg.python_exe),
        build_rule_engine_check_cmd(cfg.python_exe),
        build_forbidden_tokens_cmd(cfg.python_exe),
        build_bandit_cmd(cfg.python_exe),
        build_pip_audit_cmd(cfg.python_exe),
        build_openapi_drift_cmd(cfg.python_exe),
        build_api_reference_generated_drift_cmd(cfg.python_exe),
        build_api_reference_full_drift_cmd(cfg.python_exe),
    ]

    if cfg.run_unit:
        cmds.extend(
            [
                build_unit_tests_cmd(cfg.python_exe),
                build_unit_diff_coverage_gate_cmd(cfg.python_exe, base_ref=cfg.base_ref),
                build_unit_critical_coverage_gate_cmd(cfg.python_exe),
            ]
        )

    if cfg.run_integration:
        cmds.extend(
            [
                build_integration_tests_cmd(cfg.python_exe),
                build_integration_diff_coverage_gate_cmd(cfg.python_exe, base_ref=cfg.base_ref),
            ]
        )

    return cmds


def main(argv: Sequence[str]) -> int:
    cfg = parse_args(argv)
    if not Path("scripts/coverage_gate.py").exists():
        raise FileNotFoundError("Expected to run from repository root (scripts/coverage_gate.py missing).")

    cmds = build_commands(cfg)

    if cfg.dry_run:
        for cmd in cmds:
            print("RUN:", format_command(cmd))
        return 0

    for cmd in cmds:
        run_command(cmd)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
