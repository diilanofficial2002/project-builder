import json
from pathlib import Path
import sys
import pytest
from project_builder.application.workspace import Workspace
from project_builder.transport.api import invoke
from test_workspace import brief


@pytest.mark.skipif(sys.platform!="win32",reason="native Windows Job test")
def test_public_recipe_cannot_create_files_without_isolation(tmp_path):
    w=Workspace(tmp_path,reviewer=lambda p:True);w.init();w.start("Test a recipe")
    document=brief();document["permissions"]=["execute_recipes"]
    document["recipes"]=[{"id":"write","executable":sys.executable,
        "argv":["-c","from pathlib import Path; Path('observed.txt').write_text('actually ran')"],
        "memory_mb":24,"disk_mb":1,"timeout_seconds":5}]
    w.submit("brief",document);p=w.review_packet("kickoff");w.record_review("kickoff",p["digest"]);w.continue_run()
    state=w.status()
    result=invoke(tmp_path,"execute",{"recipe_id":"write"},request_id="execute1",expected_revision=state["revision"],run_id=state["run_id"])
    assert result["status"]=="ISOLATION_REQUIRED"
    assert not (tmp_path/"observed.txt").exists()


def test_changed_build_and_omitted_requirement_cannot_reuse_quality_review(tmp_path):
    from project_builder.application.rules import TEST_FAMILIES
    w=Workspace(tmp_path,reviewer=lambda p:True);w.init();w.start("Build")
    document=brief();document["requirements"].append({"id":"R2","summary":"Another outcome","acceptance":["Works"]})
    w.submit("brief",document);p=w.review_packet("kickoff");w.record_review("kickoff",p["digest"]);w.continue_run()
    w.submit("matrix",{"requirements":["R1"],"revision":1,"cases":[{"id":"T1","family":"functional","requirement_ids":["R1"]}],
        "families":{name:{"applicable":name=="functional","reason":"Scope assessment"} for name in TEST_FAMILIES}})
    assert not w.review_packet("matrix")["ready"]
