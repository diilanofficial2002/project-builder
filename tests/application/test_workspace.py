import importlib
import json
from pathlib import Path
import pytest

@pytest.fixture
def workspace(tmp_path):
    try:
        module=importlib.import_module("project_builder.application.workspace")
    except ModuleNotFoundError as error:
        if error.name == "project_builder.application.workspace":
            pytest.fail("Workspace workflow is not implemented")
        raise
    return module.Workspace(tmp_path, reviewer=lambda packet: True)

def brief():
    from project_builder.application.rules import DISCOVERY
    return {"answers": {key:"A concrete agreed answer" for key in DISCOVERY},
            "requirements":[{"id":"R1","summary":"A usable command","acceptance":["Returns the expected value"]}],
            "target":"final","stage_options":{},"domains":["cli"],"complexity":"mini","risks":[]}

def test_status_has_no_filesystem_side_effects(workspace):
    before=set(workspace.root.iterdir())
    assert workspace.status()["status"] == "NOT_INITIALIZED"
    assert set(workspace.root.iterdir()) == before

def test_init_and_start_are_idempotent_and_resume_survives_restart(workspace):
    workspace.init("new")
    first=workspace.start("Build a CLI")
    assert first["status"] == "DISCOVERY"
    assert workspace.start("Don't duplicate")["run_id"] == first["run_id"]
    reopened=type(workspace)(workspace.root)
    assert reopened.status()["run_id"] == first["run_id"]
    assert reopened.continue_run()["status"] == "DISCOVERY"

def test_existing_project_waits_for_real_baseline_before_kickoff(workspace):
    workspace.init("takeover"); workspace.start("Continue existing app")
    workspace.submit("brief",brief())
    assert workspace.continue_run()["status"] == "BASELINE_FEEDBACK"
    assert not workspace.review_packet("kickoff")["ready"]

def test_kickoff_is_a_digest_bound_real_review_not_an_approved_flag(workspace):
    workspace.init("new"); workspace.start("Build")
    workspace.submit("brief",brief())
    packet=workspace.review_packet("kickoff")
    assert packet["ready"] and "business_goal" in packet["content"]["answers"]
    with pytest.raises(ValueError):
        workspace.submit("brief",brief() | {"approved":True})
    assert workspace.continue_run()["status"] == "KICKOFF_REVIEW"
    workspace.record_review("kickoff",packet["digest"])
    assert workspace.continue_run()["status"] == "RUNNING"

def test_change_waits_until_whole_stage_and_stop_is_immediate(workspace):
    workspace.init("new"); workspace.start("Build"); workspace.submit("brief",brief())
    p=workspace.review_packet("kickoff"); workspace.record_review("kickoff",p["digest"])
    workspace.continue_run()
    contract=workspace.status()["contract_digest"]
    assert workspace.change("Add a report")["status"] == "QUEUED"
    assert workspace.status()["contract_digest"] == contract
    assert workspace.backlog()["review_ready"] is False
    assert workspace.pause()["status"] == "PAUSED"
    assert workspace.cancel()["status"] == "CANCELLED"

def test_stale_worker_and_duplicate_request_cannot_mutate_again(workspace):
    workspace.init("new")
    result=workspace.command("start",{"description":"Build"},request_id="request1")
    assert workspace.command("start",{"description":"Build"},request_id="request1") == result
    with pytest.raises(ValueError):
        workspace.command("start",{"description":"Different"},request_id="request1")
    old=workspace.status()["revision"]; workspace.change("Idea")
    with pytest.raises(ValueError):
        workspace.command("pause",{},request_id="request2",expected_revision=old)

def test_stage_completion_needs_current_quality_guide_and_real_feedback(workspace):
    from project_builder.application.rules import digest, TEST_FAMILIES
    workspace.init("new"); workspace.start("Build"); workspace.submit("brief",brief())
    p=workspace.review_packet("kickoff"); workspace.record_review("kickoff",p["digest"])
    workspace.continue_run()
    build=workspace.build_id()
    table={"revision":1,"requirements":["R1"],"cases":[{"id":"T1","requirement_ids":["R1"],"family":"functional","applicable":True}],
           "families":{name:{"applicable":name=="functional","reason":"Fixture scope assessment"} for name in TEST_FAMILIES}}
    workspace.submit("matrix",table)
    p=workspace.review_packet("matrix"); workspace.record_review("matrix",p["digest"])
    workspace.submit("results",{"matrix_digest":digest(table),"build_sha":build,
                               "results":[{"case_id":"T1","status":"passed","attempts":1}]})
    workspace.submit("defects",[])
    p=workspace.review_packet("quality"); workspace.record_review("quality",p["digest"])
    assert workspace.continue_run()["status"] == "VERIFYING"
    workspace.submit("guide",{"build_sha":build,"setup_steps":["Use isolated env"],
        "run_steps":["Run the example"],"stop_steps":["Stop the owned command"],"cleanup_steps":["Remove owned scratch"]})
    p=workspace.review_packet("guide"); workspace.record_review("guide",p["digest"])
    assert workspace.continue_run()["status"] == "STAGE_FEEDBACK"
    people=[{"id":f"P{i}","real_user":True,"independent":True,"unfamiliar":True,"source":f"interview-{i}"}
            for i in (1,2)]
    workspace.submit("feedback",{"build_sha":build,"participants":people,"observations":[]})
    assert workspace.continue_run()["status"] == "WAITING_FOR_HUMAN"
    p=workspace.review_packet("feedback"); workspace.record_review("feedback",p["digest"])
    assert workspace.continue_run()["status"] == "HANDOFF"
    p=workspace.review_packet("handoff"); workspace.record_review("handoff",p["digest"])
    assert workspace.continue_run()["status"] == "COMPLETED"
    assert workspace.backlog()["review_ready"]

def test_a_model_cannot_select_its_own_trusted_approval_channel(workspace):
    workspace.init("new"); workspace.start("Build"); workspace.submit("brief",brief())
    p=workspace.review_packet("kickoff")
    with pytest.raises(ValueError):
        type(workspace)(workspace.root).record_review("kickoff",p["digest"])
    assert workspace.continue_run()["status"] == "KICKOFF_REVIEW"

def test_metadata_symlink_cannot_redirect_workspace_writes(workspace,tmp_path):
    outside=tmp_path.parent/(tmp_path.name+"-outside"); outside.mkdir()
    try:
        (tmp_path/".project-builder").symlink_to(outside,target_is_directory=True)
    except OSError:
        pytest.skip("symlink privilege not available")
    with pytest.raises(ValueError):
        workspace.init("new")
    assert not list(outside.iterdir())
