from __future__ import annotations

from pathlib import Path

import yaml


def _repo_root() -> Path:
    # Navigate from apps/api/tests/unit/ to repo root.
    return Path(__file__).resolve().parents[4]


def _workflow_path(name: str) -> Path:
    return _repo_root() / ".github" / "workflows" / name


def _load_workflow(name: str) -> dict:
    return yaml.load(_workflow_path(name).read_text(encoding="utf-8"), Loader=yaml.BaseLoader)


def test_ci_workflow_has_no_mvp_disable_flag() -> None:
    workflow = _workflow_path("ci.yml")
    text = workflow.read_text(encoding="utf-8")

    assert "MVP_CI_DISABLED" not in text
    assert "env.MVP_CI_DISABLED" not in text
    assert "CI disabled notice" not in text


def test_deploy_workflow_ci_check_runs_for_workflow_run() -> None:
    workflow = _load_workflow("deploy.yml")
    ci_check = workflow["jobs"]["ci-check"]

    assert ci_check["if"] == "github.repository_owner == 'AleksNeStu'"
    guard = next(
        step
        for step in ci_check["steps"]
        if step.get("name") == "Validate triggering CI run"
    )
    assert guard["if"] == "github.event_name == 'workflow_run'"


def test_deploy_workflow_uses_triggering_sha_and_branch() -> None:
    text = _workflow_path("deploy.yml").read_text(encoding="utf-8")

    assert "github.event.workflow_run.head_sha || github.sha" in text
    assert "github.event.workflow_run.head_branch || github.ref_name" in text
    assert (
        "github.event.inputs.environment || "
        "((github.event.workflow_run.head_branch || github.ref_name) == 'dev' "
        "&& 'staging') || 'production'"
    ) in text
    assert 'ref="${{ github.sha }}"' not in text
    assert "github.ref == 'refs/heads/dev'" not in text


def test_deploy_workflow_keeps_staging_smoke_gate() -> None:
    workflow = _load_workflow("deploy.yml")
    jobs = workflow["jobs"]

    assert jobs["deploy-backend"]["needs"] == "validate"
    assert jobs["deploy-frontend"]["needs"] == "validate"
    assert set(jobs["smoke-test"]["needs"]) == {
        "deploy-backend",
        "deploy-frontend",
    }
    assert "needs.deploy-backend.result == 'success'" in jobs["smoke-test"]["if"]
    assert "needs.deploy-frontend.result == 'success'" in jobs["smoke-test"]["if"]


def test_deploy_workflow_jobs_are_owner_guarded() -> None:
    workflow = _load_workflow("deploy.yml")

    for name, job in workflow["jobs"].items():
        condition = job.get("if", "")
        assert "github.repository_owner == 'AleksNeStu'" in condition, name
