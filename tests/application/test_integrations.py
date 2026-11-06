import json
import subprocess
from pathlib import Path
import pytest

from project_builder.application.builds import build_id


def git(root, *args):
    return subprocess.run(["git", "-C", str(root), *args], check=True, capture_output=True).stdout.decode().strip()


@pytest.fixture
def repository(tmp_path):
    git(tmp_path, "init", "-b", "main")
    git(tmp_path, "config", "user.email", "test@example.invalid")
    git(tmp_path, "config", "user.name", "Fixture")
    (tmp_path / "code.txt").write_text("first")
    git(tmp_path, "add", "code.txt")
    git(tmp_path, "commit", "-m", "initial")
    return tmp_path


def test_staged_changes_invalidate_previous_test_evidence(repository):
    before = build_id(repository)
    (repository / "code.txt").write_text("different")
    git(repository, "add", "code.txt")
    assert build_id(repository) != before


def test_stage_branches_are_kept_and_feature_deletion_requires_full_merge(repository):
    from project_builder.application.git_service import LocalGit
    service = LocalGit(repository)
    service.bootstrap()
    main = git(repository, "rev-parse", "main")
    stage = service.stage("r1-final")
    feature = service.feature(stage, "hello")
    (repository / "code.txt").write_text("feature")
    git(repository, "add", "code.txt"); git(repository, "commit", "-m", "feature")
    with pytest.raises(ValueError):
        service.delete_feature(feature, stage)
    service.integrate(feature, stage)
    service.delete_feature(feature, stage)
    service.integrate(stage, "develop")
    assert git(repository, "rev-parse", "main") == main
    git(repository, "merge-base", "--is-ancestor", stage, "develop")
    assert git(repository,"show","develop:code.txt") == "feature"
    for target in ("main", "staging", "refs/heads/staging"):
        with pytest.raises(ValueError):
            service.integrate("develop", target)


def test_missing_only_bootstrap_preserves_existing_protected_refs(repository):
    from project_builder.application.git_service import LocalGit
    service = LocalGit(repository); service.bootstrap()
    refs = git(repository, "show-ref", "--heads")
    service.bootstrap()
    assert git(repository, "show-ref", "--heads") == refs
    with pytest.raises(ValueError):
        service.stage("../main")


def test_runtime_plan_never_modifies_global_python_or_user_profile(tmp_path):
    from project_builder.application.environment import environment_plan
    (tmp_path / ".python-version").write_text("3.10.13\n")
    before = list(tmp_path.iterdir())
    plan = environment_plan(tmp_path, system="Windows")
    assert plan["python_version"] == "3.10.13"
    assert plan["status"] == "PLAN_ONLY"
    assert "pyenv-win" in json.dumps(plan)
    assert list(tmp_path.iterdir()) == before
    (tmp_path / "runtime.txt").write_text("python-3.11.9")
    assert environment_plan(tmp_path, system="Windows")["status"] == "CONFLICT"


def test_noninteractive_transport_cannot_approve_user_kickoff(tmp_path):
    from project_builder.application.workspace import Workspace
    from test_workspace import brief
    w = Workspace(tmp_path); w.init(); w.start("Build"); w.submit("brief", brief())
    with pytest.raises(ValueError):
        w.record_agent_review("kickoff", w.review_packet("kickoff")["digest"], "QA checked")


def test_malformed_quality_data_is_unverified_instead_of_crashing():
    from project_builder.application.rules import evaluate_quality
    assert evaluate_quality([], {}, [], "build")["status"] == "UNVERIFIED"
