"""Task 1 boundary tests: strict data and a CLI that cannot claim service success."""

import importlib
import json
from pathlib import Path

import pytest
from pydantic import ValidationError


def contracts():
    try:
        return importlib.import_module("project_builder.contracts")
    except ModuleNotFoundError as exc:
        if exc.name in {"project_builder", "project_builder.contracts"}:
            pytest.fail("Task 1 strict contract interface has not been implemented")
        raise


def test_valid_contract_and_receipt_reference(raw_contract):
    model = contracts().StageContract.model_validate(raw_contract)
    assert model.approved_receipt_id is None
    assert model.allowed_actions == frozenset({"status"})


def test_rejects_model_claimed_approval(raw_contract):
    model = contracts().StageContract
    model.model_validate(raw_contract)
    with pytest.raises(ValidationError) as error:
        model.model_validate({**raw_contract, "approved": True})
    assert error.value.errors()[0]["loc"] == ("approved",)


@pytest.mark.parametrize("field,value", [("revision", "1"), ("revision", True), ("participant_count", True), ("participant_count", 4), ("stage", "prototype")])
def test_contract_rejects_coercion_and_invalid_values(raw_contract, field, value):
    model = contracts().StageContract
    model.model_validate(raw_contract)
    with pytest.raises(ValidationError) as error:
        model.model_validate({**raw_contract, field: value})
    assert error.value.errors()[0]["loc"] == (field,)


@pytest.mark.parametrize("field,value", [("kind", "run_arbitrary_shell"), ("argv", "echo ok; deploy")])
def test_rejects_unknown_action_and_shell_payload(raw_action, field, value):
    model = contracts().ActionRequest
    model.model_validate(raw_action)
    with pytest.raises(ValidationError) as error:
        model.model_validate({**raw_action, field: value})
    assert error.value.errors()[0]["loc"] == (field,)


@pytest.mark.parametrize("name", ["StageContract", "RunIdentity", "ActionRequest", "ApprovalReceipt", "ActionDecision", "GateResult", "CommandResult", "TeamBudget", "TeamPlan", "ScopeProfile", "RiskProfile", "CommandEnvelope"])
def test_public_models_accept_complete_examples_and_forbid_extras(contract_examples, name):
    model = getattr(contracts(), name)
    model.model_validate(contract_examples[name])
    with pytest.raises(ValidationError) as error:
        model.model_validate({**contract_examples[name], "untrusted_extra": True})
    assert error.value.errors()[0]["loc"] == ("untrusted_extra",)


def test_gate_does_not_accept_human_wait_as_evidence_pass(contract_examples):
    model = contracts().GateResult
    valid = contract_examples["GateResult"]
    model.model_validate(valid)
    with pytest.raises(ValidationError):
        model.model_validate({**valid, "status": "WAITING_FOR_HUMAN"})


def test_command_payload_discriminator_matches_intent(contract_examples):
    model = contracts().CommandEnvelope
    valid = contract_examples["CommandEnvelope"]
    model.model_validate(valid)
    with pytest.raises(ValidationError):
        model.model_validate({**valid, "payload": {"kind": "start"}})


def test_stage_report_keeps_unverified_human_state(raw_stage_report):
    contracts()
    model = importlib.import_module("project_builder.workflow.models").StageReport
    assert model.model_validate(raw_stage_report).status == "WAITING_FOR_HUMAN"
    with pytest.raises(ValidationError):
        model.model_validate({**raw_stage_report, "status": "PASS"})
    with pytest.raises(ValidationError):
        model.model_validate({**raw_stage_report, "approved": True})


def test_status_parse_is_read_only(tmp_path):
    contracts()
    cli = importlib.import_module("project_builder.cli")
    target = tmp_path / "missing-project"
    command = cli.parse_command(["status", "--project", str(target)])
    assert command.intent == "status"
    assert command.project_root == target
    assert command.payload.kind == "status"
    assert not target.exists()


@pytest.mark.parametrize("intent", ["init", "start", "continue", "status"])
def test_unavailable_services_return_failure_without_creating_project(tmp_path, capsys, intent):
    contracts()
    cli = importlib.import_module("project_builder.cli")
    target = tmp_path / "missing-project"
    assert cli.main([intent, "--project", str(target), "--json"]) != 0
    output = json.loads(capsys.readouterr().out)
    assert output["status"] == "NOT_IMPLEMENTED"
    assert output["summary"]
    assert not target.exists()


def test_text_output_is_human_readable(tmp_path, capsys):
    contracts()
    cli = importlib.import_module("project_builder.cli")
    assert cli.main(["status", "--project", str(tmp_path)]) != 0
    output = capsys.readouterr().out
    assert "NOT_IMPLEMENTED" in output
    assert "{" not in output


def test_shell_action_is_not_an_executable_cli_command(capsys):
    contracts()
    cli = importlib.import_module("project_builder.cli")
    assert cli.main(["run_arbitrary_shell", "echo ok; deploy"]) == 2
    assert "invalid choice" in capsys.readouterr().err


@pytest.mark.parametrize("kind", ["merge_staging", "push_main", "push_staging", "open_pr_main", "enable_auto_merge", "enqueue_merge", "deploy_prod", "edit_protection", "delete_main", "delete_staging"])
def test_known_forbidden_actions_are_data_only(raw_action, kind, capsys):
    assert contracts().ActionRequest.model_validate({**raw_action, "kind": kind}).kind == kind
    cli = importlib.import_module("project_builder.cli")
    assert cli.main([kind]) == 2
    assert "invalid choice" in capsys.readouterr().err


@pytest.mark.parametrize("name,field,value", [
    ("StageContract", "project_id", ""), ("StageContract", "revision", 0),
    ("StageContract", "test_matrix_revision", 0), ("StageContract", "participant_count", 2.0),
    ("RunIdentity", "contract_revision", 0), ("RunIdentity", "run_id", ""),
    ("ActionRequest", "operation_id", ""), ("ApprovalReceipt", "contract_digest", ""),
    ("TeamBudget", "max_active_specialists", 0), ("TeamBudget", "max_heavy_jobs", True),
    ("TeamPlan", "max_active_specialists", -1), ("ScopeProfile", "estimated_work", -1),
    ("ScopeProfile", "complexity", "huge"), ("RiskProfile", "security", "none"),
])
def test_shared_contract_constraints(contract_examples, name, field, value):
    model = getattr(contracts(), name)
    valid = contract_examples[name]
    model.model_validate(valid)
    with pytest.raises(ValidationError) as error:
        model.model_validate({**valid, field: value})
    assert error.value.errors()[0]["loc"][0] == field


@pytest.mark.parametrize("field", ["approved_at", "expires_at"])
def test_approval_datetimes_must_be_aware(contract_examples, field):
    model = contracts().ApprovalReceipt
    valid = contract_examples["ApprovalReceipt"]
    model.model_validate(valid)
    naive = valid["approved_at"].replace(tzinfo=None)
    with pytest.raises(ValidationError):
        model.model_validate({**valid, field: naive})


@pytest.mark.parametrize("argv,kind", [
    (["help"], "help"), (["doctor"], "doctor"), (["guide"], "guide"),
    (["backlog"], "backlog"), (["change", "test change"], "change"),
    (["feedback"], "feedback"), (["pause"], "pause"), (["stop"], "pause"),
    (["cancel"], "cancel"), (["cleanup"], "cleanup"),
])
def test_canonical_payloads_and_stop_alias(argv, kind, tmp_path):
    contracts()
    cli = importlib.import_module("project_builder.cli")
    envelope = cli.parse_command([*argv, "--project", str(tmp_path), "--json"])
    assert envelope.intent == kind
    assert envelope.payload.kind == kind
    assert envelope.payload.output_format == "json"
    assert envelope.request_id
    assert envelope.run_id is None
    assert envelope.expected_revision is None


def test_change_requires_nonempty_text():
    module = contracts()
    valid = {"request_id": "test-request", "project_root": Path("fixture"),
             "run_id": None, "expected_revision": None, "intent": "change", "payload": {"kind": "change", "text": "test change"}}
    module.CommandEnvelope.model_validate(valid)
    with pytest.raises(ValidationError):
        module.CommandEnvelope.model_validate({**valid, "payload": {"kind": "change", "text": ""}})
