"""Real SQLite tests with owned temporary databases and bounded child lifetimes."""

import hashlib
import importlib
import json
import multiprocessing
import os
import sqlite3
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from datetime import datetime

import pytest
from pydantic import ValidationError

from project_builder.contracts import RunIdentity, StageContract


def test_new_run_persists_contract_and_initial_snapshot(store, contract, state_api, database_path):
    identity = store.create_run(contract)
    snapshot = store.read_run(identity)
    assert identity.project_id == "test-project"
    assert identity.scope_id == "test-scope"
    assert identity.stage == "poc"
    assert identity.contract_revision == 3
    assert identity.run_id
    assert snapshot.identity == identity
    assert (snapshot.status, snapshot.revision) == ("INTAKE", 1)
    assert snapshot.pending_changes == snapshot.evidence_ids == []
    canonical = (
        '{"allowed_actions":["status"],"approved_receipt_id":null,'
        '"feature_ids":["test-feature"],"participant_count":2,'
        '"project_id":"test-project","requirements_version":"test-requirements-v1",'
        '"revision":3,"scope_id":"test-scope","stage":"poc","test_matrix_revision":1}'
    )
    assert snapshot.contract_digest == hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    with state_api.StateStore(database_path) as reopened:
        assert reopened.read_contract(identity) == contract
        assert reopened.read_run(identity) == snapshot
    assert store.create_run(contract) != identity


def test_digest_is_canonical_for_unicode_and_unordered_actions(store, contract):
    first = StageContract(**(contract.model_dump() | {
        "allowed_actions": frozenset({"z", "a", "ไทย"}), "scope_id": "ทดสอบ",
    }))
    second = StageContract(**dict(reversed(list(first.model_dump().items()))))
    one = store.read_run(store.create_run(first))
    two = store.read_run(store.create_run(second))
    expected = first.model_dump(mode="json")
    expected["allowed_actions"] = ["a", "z", "ไทย"]
    payload = json.dumps(expected, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    assert one.contract_digest == hashlib.sha256(payload.encode("utf-8")).hexdigest()
    assert one.contract_digest == two.contract_digest


def test_stale_writer_cannot_overwrite_new_revision(store, ready_run, state_api):
    changed = store.compare_and_set(ready_run, 1, {"status": "RUNNING"})
    assert (changed.status, changed.revision) == ("RUNNING", 2)
    with pytest.raises(state_api.StaleRevision):
        store.compare_and_set(ready_run, 1, {"status": "COMPLETED"})
    assert store.read_run(ready_run) == changed


def test_cas_persists_complete_patch_and_increments_once(store, ready_run, state_api, database_path):
    before = store.read_run(ready_run)
    result = store.compare_and_set(ready_run, 1, {
        "pending_changes": ["synthetic-change"], "evidence_ids": ["synthetic-evidence"],
    })
    assert result.revision == 2
    assert result.status == "INTAKE"
    assert result.contract_digest == before.contract_digest
    assert result.pending_changes == ["synthetic-change"]
    assert result.evidence_ids == ["synthetic-evidence"]
    with state_api.StateStore(database_path) as reopened:
        assert reopened.read_run(ready_run) == result


@pytest.mark.parametrize("patch", [
    {"identity": {}}, {"revision": 99}, {"contract_digest": "changed"},
    {"arbitrary_sql": "DROP TABLE runs"}, {"status": "MADE_UP"},
    {"pending_changes": "wrong"}, {"evidence_ids": [1]},
])
def test_invalid_patch_cannot_change_run(store, ready_run, patch):
    before = store.read_run(ready_run)
    with pytest.raises((ValueError, TypeError)):
        store.compare_and_set(ready_run, 1, patch)
    assert store.read_run(ready_run) == before


@pytest.mark.parametrize("revision", [True, 0, "1", 1.0])
def test_cas_rejects_invalid_revision(store, ready_run, revision):
    with pytest.raises((ValueError, TypeError)):
        store.compare_and_set(ready_run, revision, {"status": "RUNNING"})
    assert store.read_run(ready_run).revision == 1


@pytest.mark.parametrize("field,value", [
    ("project_id", "wrong"), ("run_id", "missing"), ("scope_id", "wrong"),
    ("stage", "mvp"), ("contract_revision", 2),
])
def test_full_identity_is_required_for_reads_and_mutations(store, ready_run, state_api, field, value):
    wrong = RunIdentity(**(ready_run.model_dump() | {field: value}))
    for read in (store.read_run, store.read_contract):
        with pytest.raises(state_api.RunNotFound):
            read(wrong)
    with pytest.raises(state_api.RunNotFound):
        store.compare_and_set(wrong, 1, {"status": "RUNNING"})
    assert store.read_run(ready_run).revision == 1


def test_two_connections_only_one_writer_can_win(database_path, state_api, store, ready_run):
    def attempt(status):
        with state_api.StateStore(database_path) as other:
            try:
                return other.compare_and_set(ready_run, 1, {"status": status})
            except state_api.StaleRevision:
                return None

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(attempt, ["RUNNING", "PAUSED"]))
    winners = [item for item in results if item is not None]
    assert len(winners) == 1
    assert store.read_run(ready_run) == winners[0]
    assert winners[0].revision == 2


def test_replayed_operation_returns_same_receipt(store, state_api):
    receipt = store.begin_operation("op-1", "same")
    assert receipt.id == "op-1"
    assert receipt.fingerprint == "same"
    assert (receipt.status, receipt.outcome) == ("UNKNOWN", None)
    assert receipt == store.begin_operation("op-1", "same")
    with pytest.raises(state_api.OperationConflict):
        store.begin_operation("op-1", "different")
    assert store.read_operation("op-1") == receipt
    assert store.read_operation("absent") is None


def test_unfinished_intent_remains_unknown_after_restart(store, database_path, state_api):
    receipt = store.begin_operation("unfinished", "same")
    store.close()
    with state_api.StateStore(database_path) as reopened:
        assert reopened.read_operation("unfinished") == receipt
        assert reopened.begin_operation("unfinished", "same").status == "UNKNOWN"


def test_completion_is_durable_and_idempotent(store, database_path, state_api):
    store.begin_operation("completed", "fingerprint")
    outcome = {"ok": True, "nested": [1, "ไทย", None]}
    receipt = store.complete_operation("completed", outcome)
    assert receipt.status == "COMPLETED"
    assert receipt.outcome == outcome
    assert store.complete_operation("completed", dict(reversed(list(outcome.items())))) == receipt
    assert store.begin_operation("completed", "fingerprint") == receipt
    with pytest.raises(state_api.OperationConflict):
        store.complete_operation("completed", {"ok": False})
    with state_api.StateStore(database_path) as reopened:
        assert reopened.read_operation("completed") == receipt
    outcome["nested"].append("mutated")
    assert store.read_operation("completed").outcome == {"ok": True, "nested": [1, "ไทย", None]}


def test_completion_requires_existing_intent(store, state_api):
    with pytest.raises(state_api.OperationConflict):
        store.complete_operation("missing", {"ok": True})
    assert store.read_operation("missing") is None


@pytest.mark.parametrize("outcome", [{"nan": float("nan")}, {"object": object()}, {1: "key"}])
def test_invalid_json_outcome_does_not_complete_intent(store, outcome):
    before = store.begin_operation("invalid-outcome", "test")
    with pytest.raises((ValueError, TypeError)):
        store.complete_operation("invalid-outcome", outcome)
    assert store.read_operation("invalid-outcome") == before


def test_sql_metacharacters_are_only_data(store):
    operation_id = "op'); DROP TABLE operations; --"
    receipt = store.begin_operation(operation_id, "'; --")
    assert store.read_operation(operation_id) == receipt
    assert store.begin_operation("still-working", "test").status == "UNKNOWN"


def test_evidence_is_durable_and_rejects_conflicting_id(store, evidence_data, state_api, database_path):
    models = importlib.import_module("project_builder.state.models")
    reference = models.EvidenceRef(**evidence_data)
    assert store.record_evidence(reference) == reference
    assert store.record_evidence(reference) == reference
    with pytest.raises(state_api.OperationConflict):
        store.record_evidence(models.EvidenceRef(**(evidence_data | {"content_digest": "changed"})))
    with state_api.StateStore(database_path) as reopened:
        assert reopened.read_evidence(reference.id) == reference
        assert reopened.read_evidence("missing") is None
    assert models.EvidenceIndex(records={reference.id: reference}).records[reference.id] == reference


@pytest.mark.parametrize("field,value", [
    ("id", ""), ("kind", ""), ("producer_id", ""), ("build_digest", ""),
    ("contract_digest", ""), ("content_digest", ""),
    ("observed_at", datetime(2026, 11, 7)), ("provenance", "trusted"),
])
def test_evidence_rejects_invalid_bindings(state_api, evidence_data, field, value):
    models = importlib.import_module("project_builder.state.models")
    with pytest.raises(ValidationError):
        models.EvidenceRef(**(evidence_data | {field: value}))


def test_state_models_are_strict(state_api, store, ready_run):
    models = importlib.import_module("project_builder.state.models")
    snapshot = store.read_run(ready_run).model_dump()
    for change in ({"revision": True}, {"revision": 0}, {"contract_digest": ""}, {"extra": 1}):
        with pytest.raises(ValidationError):
            models.RunSnapshot(**(snapshot | change))
    for change in ({"id": ""}, {"fingerprint": ""}, {"status": "FAILED"}, {"extra": 1}):
        with pytest.raises(ValidationError):
            models.OperationReceipt(**({"id": "x", "fingerprint": "y", "status": "UNKNOWN", "outcome": None} | change))


def test_database_uses_wal_and_versioned_integrity_checks(store, database_path):
    with closing(sqlite3.connect(database_path)) as connection:
        assert connection.execute("PRAGMA journal_mode").fetchone() == ("wal",)
        assert connection.execute("PRAGMA user_version").fetchone() == (1,)
        assert connection.execute("PRAGMA integrity_check").fetchall() == [("ok",)]
        assert connection.execute("PRAGMA foreign_key_check").fetchall() == []


def test_newer_schema_is_rejected_without_downgrade(database_path, state_api):
    database_path.parent.mkdir(parents=True)
    with closing(sqlite3.connect(database_path)) as connection:
        connection.execute("PRAGMA user_version = 999")
    with pytest.raises(ValueError, match="schema"):
        state_api.StateStore(database_path)
    with closing(sqlite3.connect(database_path)) as connection:
        assert connection.execute("PRAGMA user_version").fetchone() == (999,)


def test_closed_store_rejects_access_and_close_is_idempotent(store):
    store.close()
    store.close()
    with pytest.raises(sqlite3.ProgrammingError):
        store.read_operation("missing")


def _uncommitted_writer(path, run_id, channel):
    """Owned child blocks at a known transaction boundary for at most 15 seconds."""
    with closing(sqlite3.connect(path, timeout=2)) as connection:
        connection.execute("BEGIN IMMEDIATE")
        raw = connection.execute("SELECT snapshot_json FROM runs WHERE run_id = ?", (run_id,)).fetchone()[0]
        snapshot = json.loads(raw)
        snapshot.update(status="RUNNING", revision=2)
        connection.execute("UPDATE runs SET snapshot_json = ? WHERE run_id = ?", (json.dumps(snapshot), run_id))
        connection.execute("UPDATE runs SET revision = 2 WHERE run_id = ?", (run_id,))
        channel.send((os.getpid(), "uncommitted"))
        channel.poll(15)
        connection.rollback()
    channel.close()


def test_killed_uncommitted_writer_never_exposes_partial_transaction(store, ready_run, database_path, state_api):
    before = store.read_run(ready_run)
    context = multiprocessing.get_context("spawn")
    parent, child = context.Pipe()
    process = context.Process(target=_uncommitted_writer, args=(str(database_path), ready_run.run_id, child))
    process.start()
    child.close()
    try:
        assert parent.poll(10), "owned writer did not reach transaction boundary"
        assert parent.recv() == (process.pid, "uncommitted")
        assert store.read_run(ready_run) == before
        process.terminate()
        process.join(5)
        assert not process.is_alive(), "owned writer did not terminate"
        with state_api.StateStore(database_path) as reopened:
            assert reopened.read_run(ready_run) == before
            assert reopened.compare_and_set(ready_run, 1, {"status": "PAUSED"}).revision == 2
        with closing(sqlite3.connect(database_path)) as connection:
            assert connection.execute("PRAGMA integrity_check").fetchall() == [("ok",)]
    finally:
        if process.is_alive():
            process.terminate()
            process.join(5)
        if process.is_alive():
            process.kill()
            process.join(5)
        assert not process.is_alive()
        process.close()
        parent.close()
