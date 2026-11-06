"""Synthetic contract examples for automated tests only; no native evidence."""

from datetime import datetime, timezone
from pathlib import Path

import pytest


@pytest.fixture
def raw_contract():
    return {
        "project_id": "test-project", "scope_id": "test-scope", "stage": "poc",
        "revision": 1, "requirements_version": "test-requirements-v1",
        "feature_ids": ["test-feature"], "allowed_actions": frozenset({"status"}),
        "test_matrix_revision": 1, "participant_count": 2, "approved_receipt_id": None,
    }


@pytest.fixture
def raw_action():
    return {
        "kind": "open_pr_staging", "project_id": "test-project", "run_id": "test-run",
        "source_ref": "develop", "target_ref": "staging", "expected_sha": "abc123",
        "operation_id": "test-operation",
    }


@pytest.fixture
def contract_examples(raw_contract, raw_action):
    run = {
        "project_id": "test-project", "run_id": "test-run", "scope_id": "test-scope",
        "stage": "poc", "contract_revision": 1,
    }
    return {
        "StageContract": raw_contract,
        "RunIdentity": run,
        "ActionRequest": raw_action,
        "ApprovalReceipt": {
            "id": "test-receipt", "contract_digest": "test-digest", "source": "test-only",
            "event_binding": "test-event", "approved_at": datetime(2026, 11, 7, tzinfo=timezone.utc),
            "expires_at": None,
        },
        "ActionDecision": {"allowed": False, "code": "TEST_DENIED", "reasons": ["test reason"]},
        "GateResult": {"status": "UNVERIFIED", "reasons": ["test evidence absent"], "evidence_ids": []},
        "CommandResult": {"status": "NOT_IMPLEMENTED", "summary": "Unavailable", "next_action": None, "data": {}},
        "TeamBudget": {"max_active_specialists": 1, "max_heavy_jobs": 1},
        "ScopeProfile": {"feature_ids": ["test-feature"], "domains": ["cli"], "complexity": "small", "estimated_work": 1},
        "RiskProfile": {"security": "low", "privacy": "unknown", "reliability": "medium", "data_ai": "low", "unknowns": ["test unknown"]},
        "TeamPlan": {
            "selected_roles": ["BE"], "role_responsibilities": {"BE": ["test implementation"]},
            "max_active_specialists": 1, "reviewer_strategy": "test independent review",
        },
        "CommandEnvelope": {
            "request_id": "test-request", "project_root": Path("fixture"), "run_id": None,
            "expected_revision": None, "intent": "status", "payload": {"kind": "status"},
        },
    }


@pytest.fixture
def raw_stage_report(contract_examples):
    return {
        "run": contract_examples["RunIdentity"], "contract_digest": "test-contract",
        "commit_sha": "test-sha", "tree_digest": "test-tree", "env_fingerprint": "test-env",
        "matrix_revision": 1, "evidence_ids": [], "gate_ids": [], "pending_changes": [],
        "status": "WAITING_FOR_HUMAN",
    }
