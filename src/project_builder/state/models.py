"""Persistence data contracts; stored evidence is not authorization."""

from typing import Literal

from pydantic import AwareDatetime

from project_builder.contracts import NonEmptyStr, PositiveInt, RunIdentity, RunStatus, StrictModel


class RunSnapshot(StrictModel):
    identity: RunIdentity
    status: RunStatus
    revision: PositiveInt
    contract_digest: NonEmptyStr
    pending_changes: list[str]
    evidence_ids: list[str]


class OperationReceipt(StrictModel):
    id: NonEmptyStr
    fingerprint: NonEmptyStr
    status: Literal["UNKNOWN", "COMPLETED"]
    outcome: dict | None


class EvidenceRef(StrictModel):
    id: NonEmptyStr
    kind: NonEmptyStr
    producer_id: NonEmptyStr
    build_digest: NonEmptyStr
    contract_digest: NonEmptyStr
    content_digest: NonEmptyStr
    observed_at: AwareDatetime
    provenance: Literal["automated-test", "native", "human", "tool"]


class EvidenceIndex(StrictModel):
    records: dict[str, EvidenceRef]
