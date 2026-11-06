import pytest
from project_builder.application.workspace import Workspace
from test_workspace import brief


def test_unknown_action_requires_current_human_review_before_reconciliation(tmp_path):
    w=Workspace(tmp_path,reviewer=lambda p:True);w.init();w.start("Build");w.submit("brief",brief())
    p=w.review_packet("kickoff");w.record_review("kickoff",p["digest"]);w.continue_run()
    w._command("_claim_action",{"operation_id":"crashed","description":{"intent":"git","payload":{"operation":"integrate"}}})
    p=w.review_packet("recovery")
    assert p["ready"] and p["content"]["unknown_actions"]["crashed"]["status"]=="UNKNOWN"
    with pytest.raises(ValueError):
        w.record_agent_review("recovery",p["digest"],"Trust me")
    w.record_review("recovery",p["digest"])
    assert w._read()["actions"]["crashed"]["status"]=="RECONCILED_UNVERIFIED"
    assert w._read()["actions"]["crashed"]["result"]["status"]=="NOT_VERIFIED"
