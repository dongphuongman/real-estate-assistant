from __future__ import annotations

from unittest.mock import patch

import pytest

from scripts.compose_smoke import (
    SmokeConfig,
    build_compose_base_command,
    build_compose_down_command,
    build_compose_up_command,
    http_get_status,
    main,
    parse_args,
    wait_for_http_ok,
)


def test_build_compose_commands(tmp_path):
    compose_file = tmp_path / "docker-compose.yml"
    compose_file.write_text("version: '3.8'\nservices: {}\n", encoding="utf-8")

    base = build_compose_base_command(compose_file)
    assert base[:3] == ["docker", "compose", "-f"]
    assert base[3] == str(compose_file)

    up_no_build = build_compose_up_command(base, build=False)
    assert "--build" not in up_no_build

    up_build = build_compose_up_command(base, build=True)
    assert "--build" in up_build

    down = build_compose_down_command(base)
    assert down[-3:] == ["down", "--volumes", "--remove-orphans"]


def test_wait_for_http_ok_succeeds_after_retries():
    statuses = [503, 503, 200]

    def _get_status(_url: str, _timeout: float) -> int:
        return statuses.pop(0)

    sleeps: list[float] = []

    def _sleep(seconds: float) -> None:
        sleeps.append(seconds)

    wait_for_http_ok(
        "http://example/health",
        timeout_seconds=5,
        interval_seconds=0.1,
        get_status=_get_status,
        sleep=_sleep,
    )

    assert sleeps


def test_wait_for_http_ok_times_out_immediately():
    def _get_status(_url: str, _timeout: float) -> int:
        return 500

    with pytest.raises(TimeoutError):
        wait_for_http_ok(
            "http://example/health",
            timeout_seconds=0,
            interval_seconds=0.0,
            get_status=_get_status,
            sleep=lambda _: None,
        )


def test_parse_args_ci_overrides_defaults(tmp_path):
    compose_file = tmp_path / "docker-compose.yml"
    compose_file.write_text("version: '3.8'\nservices: {}\n", encoding="utf-8")

    cfg = parse_args(
        [
            "--compose-file",
            str(compose_file),
            "--timeout-seconds",
            "10",
            "--ci",
        ]
    )

    assert isinstance(cfg, SmokeConfig)
    assert cfg.build is True
    assert cfg.down is True
    assert cfg.timeout_seconds >= 240


def test_main_dry_run_prints_commands(tmp_path, capsys):
    compose_file = tmp_path / "docker-compose.yml"
    compose_file.write_text("version: '3.8'\nservices: {}\n", encoding="utf-8")

    rc = main(["--compose-file", str(compose_file), "--dry-run"])
    assert rc == 0

    out = capsys.readouterr().out
    assert "UP:" in out
    assert "DOWN:" in out
    assert "CHECK:" in out


def test_main_missing_compose_file_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        main(["--compose-file", str(tmp_path / "missing-compose.yml"), "--dry-run"])


def test_main_ci_runs_up_waits_and_tears_down(tmp_path):
    compose_file = tmp_path / "docker-compose.yml"
    compose_file.write_text("version: '3.8'\nservices: {}\n", encoding="utf-8")

    with patch("scripts.compose_smoke.run_command") as run_command_mock, patch(
        "scripts.compose_smoke.wait_for_http_ok"
    ) as wait_mock:
        rc = main(["--compose-file", str(compose_file), "--ci"])

    assert rc == 0
    assert wait_mock.call_count == 2
    assert run_command_mock.call_count == 2

    up_cmd = run_command_mock.call_args_list[0].args[0]
    down_cmd = run_command_mock.call_args_list[1].args[0]
    assert "up" in up_cmd
    assert "down" in down_cmd


def test_main_ci_tears_down_on_wait_timeout(tmp_path):
    compose_file = tmp_path / "docker-compose.yml"
    compose_file.write_text("version: '3.8'\nservices: {}\n", encoding="utf-8")

    with patch("scripts.compose_smoke.run_command") as run_command_mock, patch(
        "scripts.compose_smoke.wait_for_http_ok", side_effect=TimeoutError("boom")
    ):
        with pytest.raises(TimeoutError):
            main(["--compose-file", str(compose_file), "--ci"])

    assert run_command_mock.call_count == 2
    assert "up" in run_command_mock.call_args_list[0].args[0]
    assert "down" in run_command_mock.call_args_list[1].args[0]


def test_http_get_status_returns_http_error_code():
    import urllib.error

    err = urllib.error.HTTPError(
        url="http://example",
        code=418,
        msg="teapot",
        hdrs=None,
        fp=None,
    )
    with patch("urllib.request.urlopen", side_effect=err):
        assert http_get_status("http://example", timeout_seconds=0.1) == 418
