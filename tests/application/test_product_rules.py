"""Product rules: these stages belong to managed projects, never the plugin build."""
import importlib
import pytest

@pytest.fixture
def rules():
    try:
        return importlib.import_module("project_builder.application.rules")
    except ModuleNotFoundError as error:
        if error.name in {"project_builder.application", "project_builder.application.rules"}:
            pytest.fail("Managed-project rules are not implemented")
        raise

def matrix(total=100):
    return {"revision": 1, "requirements": ["R1"], "cases": [
        {"id": f"T{i}", "requirement_ids": ["R1"], "tags": ["functional", "regression"], "applicable": True}
        for i in range(total)]}

def evidence(rules, table, passed=96):
    return {"matrix_digest": rules.digest(table), "build_sha": "build-a",
            "results": [{"case_id": case["id"], "status": "passed" if i < passed else "failed",
                         "attempts": 1} for i, case in enumerate(table["cases"])]}

def test_fewest_stages_is_not_a_fixed_ladder(rules):
    assert rules.select_stages("final") == ["final"]
    assert rules.select_stages("mvp", feasibility_unknown=True) == ["poc", "mvp"]
    assert rules.select_stages("final", first_slice_needed=True, pilot_needed=True) == ["mvp", "beta", "final"]

def test_takeover_and_new_version_require_baseline_before_kickoff(rules):
    assert rules.intake_step("new") == "DISCOVERY"
    for kind in ("takeover", "new-version"):
        assert rules.intake_step(kind) == "BASELINE_FEEDBACK"

@pytest.mark.parametrize("passed,status", [(95, "FAIL"), (96, "PASS")])
def test_quality_strictly_above_95(rules, passed, status):
    table=matrix()
    assert rules.evaluate_quality(table, evidence(rules, table, passed), [], "build-a")["status"] == status

@pytest.mark.parametrize("severity", ["high", "critical", "unknown"])
def test_high_or_unknown_severity_cannot_be_hidden(rules, severity):
    table=matrix()
    result=rules.evaluate_quality(table, evidence(rules, table, 100),
                                  [{"id":"D1","severity":severity,"status":"open"}], "build-a")
    assert result["status"] != "PASS"

def test_tags_missing_results_and_retries_do_not_inflate_quality(rules):
    table=matrix(2)
    data=evidence(rules, table, 2)
    data["results"]=[{"case_id":"T0","status":"passed","attempts":2}]
    result=rules.evaluate_quality(table, data, [], "build-a")
    assert (result["passed"],result["total"]) == (0,2)
    assert result["status"] == "FAIL"

def test_empty_duplicate_stale_or_uncovered_matrix_is_unverified(rules):
    for table in [matrix(0), {"revision":1,"requirements":["R1","R2"],"cases":matrix(1)["cases"]}]:
        assert rules.evaluate_quality(table, evidence(rules,table), [], "build-a")["status"] == "UNVERIFIED"
    table=matrix(2); table["cases"][1]["id"]="T0"
    assert rules.evaluate_quality(table,evidence(rules,table),[],"build-a")["status"] == "UNVERIFIED"
    table=matrix()
    assert rules.evaluate_quality(table,evidence(rules,table),[],"other-build")["status"] == "UNVERIFIED"

def test_duplicate_result_ids_are_not_last_write_wins(rules):
    table=matrix(1); data=evidence(rules,table,1)
    data["results"].append({"case_id":"T0","status":"passed","attempts":1})
    assert rules.evaluate_quality(table,data,[],"build-a")["status"] == "UNVERIFIED"

def test_team_is_scope_sensitive_not_full_organization(rules):
    small=rules.plan_team(["cli"], "mini", [])
    assert small["max_active_specialists"] == 1
    assert "ai-engineer" not in small["selected_roles"]
    rich=rules.plan_team(["frontend","backend","data","ai"], "large", ["security"])
    for role in ["ux-ui-designer","frontend","backend","data-engineer","ai-engineer","devsecops"]:
        assert role in rich["selected_roles"]

def test_real_participants_are_independent_and_not_simulated(rules):
    people=[{"id":"P1","real_user":True,"independent":True,"unfamiliar":True,"source":"interview-1"},
            {"id":"P2","real_user":True,"independent":True,"unfamiliar":True,"source":"interview-2"}]
    assert rules.feedback_check(people)["status"] == "PASS"
    assert rules.feedback_check(people[:1])["status"] == "WAITING_FOR_HUMAN"
    people[1]["source"]="synthetic"
    assert rules.feedback_check(people)["status"] != "PASS"

def test_kickoff_interview_spans_business_and_technical(rules):
    gaps=rules.discovery_questions({})
    for field in ["business_goal","users","scope","acceptance","architecture","runtime","authority","resource_budget"]:
        assert field in {q["field"] for q in gaps}
    assert rules.discovery_questions({"business_goal":"save time"})[0]["field"] != "business_goal"
