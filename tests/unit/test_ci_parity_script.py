from __future__ import annotations

import sys

import pytest

from scripts.ci_parity import (
    ParityConfig,
    build_commands,
    build_integration_diff_coverage_gate_cmd,
    build_unit_diff_coverage_gate_cmd,
    format_command,
    parse_args,
)


def test_parse_args_defaults_run_unit_and_integration() -> None:
    cfg = parse_args([])
    assert cfg.run_unit is True
    assert cfg.run_integration is True
    assert cfg.dry_run is False
    assert cfg.python_exe


def test_parse_args_unit_only_disables_integration() -> None:
    cfg = parse_args(["--unit-only"])
    assert cfg.run_unit is True
    assert cfg.run_integration is False


def test_parse_args_integration_only_disables_unit() -> None:
    cfg = parse_args(["--integration-only"])
    assert cfg.run_unit is False
    assert cfg.run_integration is True


def test_build_unit_diff_coverage_gate_cmd_includes_base_ref_when_provided() -> None:
    cmd = build_unit_diff_coverage_gate_cmd("python", base_ref="origin/main")
    assert "--base-ref" in cmd
    assert "origin/main" in cmd


def test_build_unit_diff_coverage_gate_cmd_omits_base_ref_when_missing() -> None:
    cmd = build_unit_diff_coverage_gate_cmd("python", base_ref=None)
    assert "--base-ref" not in cmd


def test_build_integration_diff_coverage_gate_cmd_includes_base_ref_when_provided() -> None:
    cmd = build_integration_diff_coverage_gate_cmd("python", base_ref="origin/main")
    assert "--base-ref" in cmd
    assert "origin/main" in cmd


def test_format_command_returns_string() -> None:
    assert isinstance(format_command([sys.executable, "-c", "print('x')"]), str)


@pytest.mark.parametrize(
    ("run_unit", "run_integration", "expected_contains"),
    [
        (True, True, ("tests/unit", "tests/integration")),
        (True, False, ("tests/unit",)),
        (False, True, ("tests/integration",)),
    ],
)
def test_build_commands_includes_expected_test_scopes(
    run_unit: bool, run_integration: bool, expected_contains: tuple[str, ...]
) -> None:
    cfg = ParityConfig(
        python_exe=sys.executable,
        base_ref=None,
        run_unit=run_unit,
        run_integration=run_integration,
        dry_run=True,
    )
    cmds = build_commands(cfg)
    flat = " ".join(" ".join(cmd) for cmd in cmds)
    for token in expected_contains:
        assert token in flat
