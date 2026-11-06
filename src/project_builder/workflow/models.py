"""Workflow report data independent of future workflow services."""

from project_builder.contracts import NonEmptyStr, PositiveInt, RunIdentity, RunStatus, StrictModel


class StageReport(StrictModel):
    run: RunIdentity
    contract_digest: NonEmptyStr
    commit_sha: NonEmptyStr
    tree_digest: NonEmptyStr
    env_fingerprint: NonEmptyStr
    matrix_revision: PositiveInt
    evidence_ids: list[NonEmptyStr]
    gate_ids: list[NonEmptyStr]
    pending_changes: list[str]
    status: RunStatus
