import importlib.util
from pathlib import Path


def _load_start_module():
    root = Path(__file__).resolve().parents[3]
    start_path = root / "scripts" / "dev" / "start.py"
    spec = importlib.util.spec_from_file_location("scripts_dev_start", start_path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_docker_gpu_available_false_when_docker_missing(monkeypatch):
    m = _load_start_module()
    monkeypatch.setattr(m.shutil, "which", lambda _name: None)
    assert m._docker_gpu_available() is False


def test_docker_mode_gpu_includes_profile_in_dry_run(capsys):
    m = _load_start_module()
    rc = m.main(["--mode", "docker", "--docker-mode", "gpu", "--dry-run"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "--profile gpu" in out

