import pytest
from project_builder.application.workspace import Workspace
from project_builder.transport.api import invoke
from test_workspace import brief

def capabilities(**changes):
    return {"host":"codex","run_tool":"exec_command","stop_tool":"write_stdin",
            "bounded_timeout":True,"owned_cleanup":True,"observed_from":"Available host tool schemas",**changes}

def test_native_host_tools_do_not_require_an_optional_standalone_executor(tmp_path):
    workspace=Workspace(tmp_path,reviewer=lambda p:True);workspace.init();workspace.start("Build")
    document=brief();document["permissions"]=["native_tools"]
    workspace.submit("brief",document);packet=workspace.review_packet("kickoff")
    workspace.record_review("kickoff",packet["digest"]);workspace.continue_run()
    result=invoke(tmp_path,"native-plan",{"capabilities":capabilities()})
    assert result["status"]=="HOST_NATIVE"
    assert result["max_active_heavy_jobs"]==1
    assert result["requires_custom_runner"] is False
    assert "merge_staging" in result["forbidden_actions"]

def test_native_route_requires_reviewed_scope_and_real_lifecycle_capabilities(tmp_path):
    from project_builder.application.native_host import execution_route
    assert execution_route(capabilities(),authorized=False)["status"]=="NOT_AUTHORIZED"
    assert execution_route(capabilities(owned_cleanup=False),authorized=True)["status"]=="HOST_CAPABILITY_REQUIRED"
    assert execution_route(capabilities(bounded_timeout=False),authorized=True)["status"]=="HOST_CAPABILITY_REQUIRED"

@pytest.mark.parametrize("status,proof,expected",[("ACTIVE",None,"CLEANUP_PENDING"),("CLEANUP_PENDING",None,"CLEANUP_PENDING"),
    ("CLEANED",None,"UNVERIFIED"),("CLEANED","tool-session/exit-0-and-owned-processes-stopped","PASS")])
def test_native_job_state_blocks_handoff_until_owned_cleanup_evidence(status,proof,expected):
    from project_builder.application.native_host import native_jobs_gate
    work={"native_jobs":[{"id":"session1","host":"codex","run_id":"run1","status":status,"cleanup_evidence":proof}]}
    assert native_jobs_gate(work,"run1")["status"]==expected
    assert native_jobs_gate(work,"different-run")["status"]!="PASS"

def test_no_native_work_is_explicit_not_an_invented_cleanup_receipt():
    from project_builder.application.native_host import native_jobs_gate
    assert native_jobs_gate({},"run1")["status"]=="UNVERIFIED"
    assert native_jobs_gate({"native_jobs":[],"no_native_jobs_reason":"All checks were manual"},"run1")["status"]=="PASS"

def active_workspace(tmp_path):
    workspace=Workspace(tmp_path,reviewer=lambda p:True);workspace.init();workspace.start("Build")
    workspace.submit("brief",brief()|{"permissions":["native_tools"]})
    packet=workspace.review_packet("kickoff");workspace.record_review("kickoff",packet["digest"])
    workspace.continue_run()
    job={"id":"owned-session-1","host":"codex","run_id":workspace.status()["run_id"],"status":"ACTIVE"}
    workspace.submit("work",{"native_jobs":[job]})
    return workspace,job

def test_cancel_does_not_claim_host_jobs_were_killed_and_can_record_later_cleanup(tmp_path):
    workspace,job=active_workspace(tmp_path)
    response=invoke(tmp_path,"cancel",{},request_id="cancel1",expected_revision=workspace.status()["revision"])
    assert response["status"]=="CANCELLED"
    assert response["cleanup"]["status"]=="CLEANUP_PENDING"
    assert not workspace.review_packet("handoff")["ready"]
    with pytest.raises(ValueError,match="workloads"):
        workspace.start("Another project scope")
    with pytest.raises(ValueError):
        workspace.submit("work",{"native_jobs":[],"no_native_jobs_reason":"Forget that session"})
    workspace.submit("work",{"native_jobs":[job|{"status":"CLEANED","cleanup_evidence":"Native stop/poll tool: exit confirmed; child tree and scratch checked"}]})
    result=invoke(tmp_path,"cleanup",{},request_id="cleanup1",expected_revision=workspace.status()["revision"])
    assert result["status"]=="CLEANED"
    assert workspace.start("Another project scope")["run_id"]!=job["run_id"]

def test_active_workload_cannot_disappear_from_work_updates(tmp_path):
    workspace,job=active_workspace(tmp_path)
    with pytest.raises(ValueError):
        workspace.submit("work",{"native_jobs":[],"no_native_jobs_reason":"No jobs"})
    assert invoke(tmp_path,"status")["native_resources"]["status"]=="CLEANUP_PENDING"

def test_native_plan_cannot_grant_permission_after_pause_or_accept_stale_run(tmp_path):
    workspace,_=active_workspace(tmp_path);workspace.pause()
    assert invoke(tmp_path,"native-plan",{"capabilities":capabilities()})["status"]=="NOT_AUTHORIZED"
    with pytest.raises(ValueError,match="stale run"):
        invoke(tmp_path,"native-plan",{"capabilities":capabilities()},run_id="previous-run")

@pytest.mark.parametrize("change",[{"run_id":"stale"},{"status":["ACTIVE"]},{"host":"invented"},{"status":"CLEANED","cleanup_evidence":""}])
def test_invalid_native_records_do_not_break_status_or_hide_cleanup(tmp_path,change):
    workspace,job=active_workspace(tmp_path)
    with pytest.raises(ValueError):
        workspace.submit("work",{"native_jobs":[job|change]})
    assert invoke(tmp_path,"status")["native_resources"]["status"]=="CLEANUP_PENDING"

def test_cancelled_cleanup_update_cannot_rewrite_a_job_command(tmp_path):
    workspace,job=active_workspace(tmp_path)
    workspace.submit("work",{"native_jobs":[job|{"command":"original command"}]})
    workspace.cancel()
    with pytest.raises(ValueError):
        workspace.submit("work",{"native_jobs":[job|{"command":"rewritten command","status":"CLEANED","cleanup_evidence":"proof"}]})

def test_native_plan_cli_reads_same_reviewed_state_and_never_runs_a_command(tmp_path,capsys):
    import json
    from project_builder.cli import main
    workspace,_=active_workspace(tmp_path)
    path=tmp_path/"capabilities.json";path.write_text(json.dumps(capabilities()),encoding="utf-8")
    revision=workspace.status()["revision"]
    assert main(["native-plan",str(path),"--project",str(tmp_path),"--json"])==0
    response=json.loads(capsys.readouterr().out)
    assert response["data"]["status"]=="HOST_NATIVE"
    assert workspace.status()["revision"]==revision
