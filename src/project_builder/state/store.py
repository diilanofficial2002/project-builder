"""Durable local state and receipts, with no workflow or external side effects.

The caller supplies an owned runtime path (later provided by PlatformPaths).
UNKNOWN receipts survive restart and require reconciliation before any retry of
an external effect. Evidence persistence alone does not establish trust.
"""

import hashlib
import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator, Self
from uuid import uuid4

from pydantic import TypeAdapter

from project_builder.contracts import PositiveInt, RunIdentity, StageContract
from project_builder.state.models import EvidenceRef, OperationReceipt, RunSnapshot


class StaleRevision(ValueError):
    """A writer no longer owns the state revision it read."""


class RunNotFound(LookupError):
    """No run matches the complete supplied identity."""


class OperationConflict(ValueError):
    """An existing receipt or evidence identifier has conflicting content."""


def _json(value: object) -> str:
    """Canonical, lossless JSON data; reject values JSON would silently coerce."""
    def check(item: object) -> None:
        if type(item) is dict:
            for key, nested in item.items():
                if type(key) is not str:
                    raise ValueError("JSON object keys must be strings")
                check(nested)
        elif type(item) is list:
            for nested in item:
                check(nested)
        elif item is not None and type(item) not in (str, int, float, bool):
            raise ValueError("value is not JSON data")

    check(value)
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)


class StateStore:
    """One explicitly opened SQLite connection, closed by the owning caller.

    Independent instances can coordinate through the same database. SQLite's
    bounded writer lock serializes transactions; CAS rejects stale writers.
    Each instance follows sqlite3's same-thread connection ownership rule.
    """

    def __init__(self, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        self._connection = sqlite3.connect(path, timeout=2, isolation_level=None)
        try:
            self._connection.execute("PRAGMA busy_timeout = 2000")
            self._connection.execute("PRAGMA foreign_keys = ON")
            self._check_schema_version()
            self._connection.execute("PRAGMA journal_mode = WAL")
            self._connection.execute("PRAGMA synchronous = FULL")
            with self._transaction():
                version = self._check_schema_version()
                if version == 0:
                    migration = Path(__file__).with_name("migrations") / "001_initial.sql"
                    statement = ""
                    for line in migration.read_text(encoding="utf-8").splitlines(keepends=True):
                        statement += line
                        if sqlite3.complete_statement(statement):
                            self._connection.execute(statement)
                            statement = ""
                    if statement.strip():
                        raise ValueError("incomplete schema migration")
                    self._connection.execute("PRAGMA user_version = 1")
            if self._connection.execute("PRAGMA quick_check").fetchall() != [("ok",)]:
                raise sqlite3.DatabaseError("state database integrity check failed")
            if self._connection.execute("PRAGMA foreign_key_check").fetchall():
                raise sqlite3.IntegrityError("state database foreign key check failed")
        except BaseException:
            self.close()
            raise

    def _check_schema_version(self) -> int:
        version = self._connection.execute("PRAGMA user_version").fetchone()[0]
        if version not in (0, 1):
            raise ValueError(f"unsupported state schema version: {version}")
        return version

    @contextmanager
    def _transaction(self) -> Iterator[None]:
        self._connection.execute("BEGIN IMMEDIATE")
        try:
            yield
            self._connection.commit()
        except BaseException:
            self._connection.rollback()
            raise

    def create_run(self, contract: StageContract) -> RunIdentity:
        # Validate a fresh copy even if the caller mutated a previously valid model.
        contract = StageContract.model_validate(contract.model_dump())
        data = contract.model_dump(mode="json")
        data["allowed_actions"] = sorted(contract.allowed_actions)
        contract_json = _json(data)
        identity = RunIdentity(
            project_id=contract.project_id, run_id=str(uuid4()), scope_id=contract.scope_id,
            stage=contract.stage, contract_revision=contract.revision,
        )
        snapshot = RunSnapshot(
            identity=identity, status="INTAKE", revision=1,
            contract_digest=hashlib.sha256(contract_json.encode("utf-8")).hexdigest(),
            pending_changes=[], evidence_ids=[],
        )
        with self._transaction():
            self._connection.execute(
                "INSERT INTO runs (run_id, revision, snapshot_json, contract_json) VALUES (?, ?, ?, ?)",
                (identity.run_id, 1, _json(snapshot.model_dump(mode="json")), contract_json),
            )
        return identity

    def _read_run_row(self, run: RunIdentity) -> tuple:
        run = RunIdentity.model_validate(run.model_dump())
        row = self._connection.execute(
            "SELECT revision, snapshot_json, contract_json FROM runs WHERE run_id = ?", (run.run_id,),
        ).fetchone()
        if row is None or RunSnapshot.model_validate_json(row[1]).identity != run:
            raise RunNotFound("no run matches the supplied identity")
        return row

    def read_run(self, run: RunIdentity) -> RunSnapshot:
        return RunSnapshot.model_validate_json(self._read_run_row(run)[1])

    def read_contract(self, run: RunIdentity) -> StageContract:
        return StageContract.model_validate_json(self._read_run_row(run)[2])

    def compare_and_set(self, run: RunIdentity, expected_revision: int, patch: dict) -> RunSnapshot:
        TypeAdapter(PositiveInt).validate_python(expected_revision, strict=True)
        if type(patch) is not dict or patch.keys() - {"status", "pending_changes", "evidence_ids"}:
            raise ValueError("patch may only contain status, pending_changes and evidence_ids")
        with self._transaction():
            row = self._read_run_row(run)
            if row[0] != expected_revision:
                raise StaleRevision("run state revision has changed")
            data = RunSnapshot.model_validate_json(row[1]).model_dump()
            snapshot = RunSnapshot.model_validate(data | patch | {"revision": expected_revision + 1})
            changed = self._connection.execute(
                "UPDATE runs SET revision = ?, snapshot_json = ? WHERE run_id = ? AND revision = ?",
                (snapshot.revision, _json(snapshot.model_dump(mode="json")), run.run_id, expected_revision),
            )
            if changed.rowcount != 1:
                raise StaleRevision("run state revision has changed")
        return snapshot

    def begin_operation(self, operation_id: str, fingerprint: str) -> OperationReceipt:
        intent = OperationReceipt(id=operation_id, fingerprint=fingerprint, status="UNKNOWN", outcome=None)
        with self._transaction():
            previous = self.read_operation(operation_id)
            if previous is not None:
                if previous.fingerprint != fingerprint:
                    raise OperationConflict("operation fingerprint differs from persisted intent")
                return previous
            self._connection.execute(
                "INSERT INTO operations (operation_id, receipt_json) VALUES (?, ?)",
                (operation_id, _json(intent.model_dump(mode="json"))),
            )
        return intent

    def complete_operation(self, operation_id: str, outcome: dict) -> OperationReceipt:
        if type(outcome) is not dict:
            raise ValueError("operation outcome must be a JSON object")
        outcome_json = _json(outcome)
        with self._transaction():
            previous = self.read_operation(operation_id)
            if previous is None:
                raise OperationConflict("operation has no persisted intent")
            if previous.status == "COMPLETED":
                if _json(previous.outcome) != outcome_json:
                    raise OperationConflict("operation outcome differs from persisted completion")
                return previous
            receipt = OperationReceipt(
                id=previous.id, fingerprint=previous.fingerprint,
                status="COMPLETED", outcome=json.loads(outcome_json),
            )
            self._connection.execute(
                "UPDATE operations SET receipt_json = ? WHERE operation_id = ?",
                (_json(receipt.model_dump(mode="json")), operation_id),
            )
        return receipt

    def read_operation(self, operation_id: str) -> OperationReceipt | None:
        row = self._connection.execute(
            "SELECT receipt_json FROM operations WHERE operation_id = ?", (operation_id,),
        ).fetchone()
        return OperationReceipt.model_validate_json(row[0]) if row is not None else None

    def record_evidence(self, reference: EvidenceRef) -> EvidenceRef:
        """Internal persistence only; callers must verify trust before ingestion."""
        reference = EvidenceRef.model_validate(reference.model_dump())
        with self._transaction():
            previous = self.read_evidence(reference.id)
            if previous is not None:
                if previous != reference:
                    raise OperationConflict("evidence content differs from persisted reference")
                return previous
            self._connection.execute(
                "INSERT INTO evidence (evidence_id, reference_json) VALUES (?, ?)",
                (reference.id, _json(reference.model_dump(mode="json"))),
            )
        return reference

    def read_evidence(self, id: str) -> EvidenceRef | None:
        row = self._connection.execute(
            "SELECT reference_json FROM evidence WHERE evidence_id = ?", (id,),
        ).fetchone()
        return EvidenceRef.model_validate_json(row[0]) if row is not None else None

    def close(self) -> None:
        self._connection.close()

    def __enter__(self) -> Self:
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        self.close()
