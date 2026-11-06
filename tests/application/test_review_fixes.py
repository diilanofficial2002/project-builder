import importlib.util
import json
import re
from pathlib import Path
import pytest
from project_builder.application.workspace import Workspace
from project_builder.application.rules import digest
from project_builder.transport.api import invoke
from test_workspace import brief
from test_integrations import repository,git

@pytest.mark.parametrize("key",["filter.review.smudge","filter.review.clean","filter.review.process","merge.review.driver"])
def test_local_git_refuses_executable_extensions_without_rewriting_config(repository,key):
    from project_builder.application.git_service import LocalGit
    service=LocalGit(repository);service.bootstrap()
    (repository/".gitattributes").write_text("code.txt "+("merge=review" if key.startswith("merge.") else "filter=review")+"\n")
    git(repository,"add",".gitattributes");git(repository,"commit","-m","attributes")
    git(repository,"config",key,"python untrusted-script.py")
    with pytest.raises(ValueError,match="executable Git"):
        service.stage("review-final")
    assert git(repository,"config","--get",key)=="python untrusted-script.py"

def test_public_recipe_cannot_write_protected_git_even_after_user_review(repository):
    import shutil
    tmp_path=repository
    before=git(repository,"rev-parse","main")
    w=Workspace(tmp_path,reviewer=lambda p:True);w.init();w.start("Build")
    document=brief();document["permissions"]=["execute_recipes"]
    document["recipes"]=[{"id":"anything","executable":shutil.which("git"),"argv":["update-ref","-d","refs/heads/main"],"memory_mb":24,"timeout_seconds":5}]
    w.submit("brief",document);p=w.review_packet("kickoff");w.record_review("kickoff",p["digest"]);w.continue_run()
    state=w.status()
    result=invoke(tmp_path,"execute",{"recipe_id":"anything"},request_id="denied",expected_revision=state["revision"])
    assert result["status"]=="ISOLATION_REQUIRED"
    assert git(repository,"rev-parse","main")==before
    assert not w._read().get("actions")

def test_pending_scratch_is_not_lost_after_workload_capacity_is_released(tmp_path,monkeypatch):
    from project_builder.platform_paths import PlatformPaths
    from project_builder.application.execution import pending_resources,cleanup_project
    from project_builder.supervision.ledger import ResourceLedger
    from project_builder.supervision.models import ResourceRequest,MachineSample,ResourceHandle,CleanupReceipt
    from project_builder.supervision.ledger import admit
    from project_builder.contracts import RunIdentity
    import psutil,os
    root=tmp_path/"machine";ledger=ResourceLedger(root)
    monkeypatch.setattr(PlatformPaths,"user_state_root",staticmethod(lambda:root))
    request=ResourceRequest(project_id="owned",memory_bytes=1)
    sample=MachineSample(total_ram_bytes=8*2**30,available_ram_bytes=6*2**30,disk_total_bytes=100*2**30,disk_free_bytes=50*2**30)
    lease=admit(request,sample,ledger).lease_id
    scratch=root/"scratch"/"handle";scratch.mkdir(parents=True);(scratch/".owner").write_text("token")
    handle=ResourceHandle(id="handle",owner=RunIdentity(project_id="owned",run_id="r",scope_id="s",stage="final",contract_revision=1),
        pid=2147483000,process_started_at=1.0,process_group_id=None,owned_paths=[scratch],lease_id=lease,owner_token="token",containment="contained_tree")
    ledger.persist(handle,os.getpid(),psutil.Process().create_time())
    ledger.release(lease);ledger.save_receipt(CleanupReceipt(handle_id="handle",status="CLEANUP_PENDING",reason="scratch deferred",workload_stopped=True))
    assert pending_resources("owned")
    result=cleanup_project("owned")
    assert result["status"]=="CLEANED" and result["receipts"]
    assert not scratch.exists()
    assert not pending_resources("owned")

def test_completed_scope_keeps_guide_and_evidence_when_next_run_starts(tmp_path):
    w=Workspace(tmp_path);w.init();old_run=w.start("Old scope")["run_id"]
    def completed(doc):
        doc["run"]["status"]="COMPLETED";doc["artifacts"]["guide"]={"run_steps":["old guide"]}
        return {"status":"COMPLETED"}
    w._paths().mutate("fixture-completed",{},completed)
    w.start("Next scope")
    assert w._read()["archive"][0]["artifacts"]["guide"]["run_steps"]==["old guide"]
    assert invoke(tmp_path,"guide",run_id=old_run)["guide"]["run_steps"]==["old guide"]

def test_every_advertised_link_and_template_exists_in_generated_package(tmp_path):
    root=Path(__file__).resolve().parents[2]
    spec=importlib.util.spec_from_file_location("builder",root/"scripts"/"build_packages.py")
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    runtime=tmp_path/"runtime";runtime.mkdir();(runtime/"project-builder.exe").write_bytes(b"fixture")
    module.package(root,runtime,tmp_path/"output",platform_name="windows-x64")
    for host in ("codex","claude","devin"):
        package=tmp_path/"output"/host/"project-builder"
        for link in re.findall(r"\]\(([^)]+)\)",(package/"README.md").read_text(encoding="utf-8")):
            if not link.startswith("https:"): assert (package/link).is_file(),link
        assert json.loads((package/"templates"/"brief.json").read_text())["requirements"]
        assert (package/"examples"/"marketplace.json").is_file()
