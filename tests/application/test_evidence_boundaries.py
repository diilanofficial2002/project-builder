from project_builder.application.rules import digest,evaluate_quality,feedback_check
from project_builder.application.workspace import Workspace
from test_workspace import brief

def test_closed_high_defect_without_fix_and_retest_is_unverified():
    matrix={"revision":1,"requirements":["R1"],"cases":[{"id":"T1","requirement_ids":["R1"]}]}
    results={"matrix_digest":digest(matrix),"build_sha":"build","results":[{"case_id":"T1","status":"passed"}]}
    assert evaluate_quality(matrix,results,[{"id":"D1","severity":"high","status":"closed"}],"build")["status"]=="UNVERIFIED"

def test_malformed_people_never_count_as_human_feedback():
    assert feedback_check([True,False])["status"]=="WAITING_FOR_HUMAN"

def test_vague_todo_discovery_template_does_not_unlock_kickoff(tmp_path):
    w=Workspace(tmp_path);w.init();w.start("Build")
    document=brief();document["answers"]["business_goal"]="TODO"
    w.submit("brief",document)
    assert not w.review_packet("kickoff")["ready"]
