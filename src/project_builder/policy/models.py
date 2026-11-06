"""Policy data and internal trust boundary; none of these objects grant trust alone.

GateEvidence and AuthorityResolver are runtime dependencies, never MCP payloads.
StateStore authenticates neither producers nor artifact contents: a resolver must
verify those, the approval channel, and an authenticated enforcement receipt.
"""

import hashlib
import json
import re
from dataclasses import dataclass
from typing import Literal, Protocol, Self

from pydantic import AwareDatetime, ConfigDict, model_validator

from project_builder.contracts import ActionRequest, NonEmptyStr, PositiveInt, RunIdentity, StrictModel
from project_builder.state.models import EvidenceRef
from project_builder.state.store import StateStore


def digest_data(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
        ensure_ascii=False, allow_nan=False).encode("utf-8")).hexdigest()


class RepositoryRef(StrictModel):
    """Trusted onboarding scope; numeric GitHub ID detects renamed/transferred repos."""

    model_config = ConfigDict(strict=True, extra="forbid", frozen=True)
    project_id: NonEmptyStr
    repository_id: PositiveInt
    owner: NonEmptyStr
    name: NonEmptyStr
    remote_url: NonEmptyStr

    @model_validator(mode="after")
    def scoped_github_remote(self) -> Self:
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9-]*", self.owner):
            raise ValueError("invalid GitHub owner")
        if not re.fullmatch(r"[A-Za-z0-9_][A-Za-z0-9_.-]*", self.name) or self.name in {".", ".."}:
            raise ValueError("invalid GitHub repository name")
        path = f"{self.owner}/{self.name}"
        allowed = {f"https://github.com/{path}", f"https://github.com/{path}.git",
            f"git@github.com:{path}", f"git@github.com:{path}.git",
            f"ssh://git@github.com/{path}", f"ssh://git@github.com/{path}.git"}
        if self.remote_url not in allowed:
            raise ValueError("remote is outside the exact onboarded github.com repository")
        return self


class RemoteIdentity(StrictModel):
    model_config = ConfigDict(strict=True, extra="forbid", frozen=True)
    actor_id: PositiveInt
    login: NonEmptyStr


class EnforcementReport(StrictModel):
    """Immutable observations. VERIFIED is data, not authenticated provenance."""

    model_config = ConfigDict(strict=True, extra="forbid", frozen=True)
    mode: Literal["LOCAL_ONLY", "VERIFIED"]
    repo: RepositoryRef
    actor_id: PositiveInt
    refs_digest: NonEmptyStr
    rules_digest: NonEmptyStr
    workflows_digest: NonEmptyStr
    checked_at: AwareDatetime
    expires_at: AwareDatetime
    reasons: tuple[str, ...]
    refs: tuple[tuple[str, str], ...] = ()


def digest_refs(refs: tuple[tuple[str, str], ...]) -> str:
    return digest_data(sorted(refs))


def report_digest(report: EnforcementReport) -> str:
    return digest_data(report.model_dump(mode="json"))


@dataclass(frozen=True)
class VerifiedBindings:
    """Resolver result, NEVER deserialized from commands or inferred from rows.

The resolver must authenticate proof_digest against an inspection receipt, read
current repo/actor/config, validate approval expiry/channel/contract, evaluate all
gates for the action, and hash the actual evidence artifacts. It returns None if
any prerequisite is unknown. A caller-supplied VERIFIED report is insufficient.
"""

    repo: RepositoryRef
    actor_id: int
    state_revision: int
    contract_digest: str
    refs_digest: str
    rules_digest: str
    workflows_digest: str
    proof_digest: str
    approval_receipt_id: str
    evidence_digests: tuple[tuple[str, str], ...]
    build_digest: str


class AuthorityResolver(Protocol):
    def resolve(self, *, run: RunIdentity, action: ActionRequest, contract_digest: str,
                proof: EnforcementReport, references: tuple[EvidenceRef, ...]) -> VerifiedBindings | None:
        """Resolve only from trusted runtime services; model arguments supply no trust."""
        ...


@dataclass(frozen=True)
class GateEvidence:
    """Internal live state handle. Loading IDs is not a passed/approved flag."""

    store: StateStore
    run: RunIdentity
    expected_revision: int
    resolver: AuthorityResolver | None


def load_gate_evidence(store: StateStore, run: RunIdentity, expected_revision: int,
                       *, resolver: AuthorityResolver | None = None) -> GateEvidence:
    """Wire from service composition only; authorize re-reads rows on every call."""
    if type(expected_revision) is not int or expected_revision < 1:
        raise ValueError("expected_revision must be positive")
    run = RunIdentity.model_validate(run.model_dump())
    store.read_run(run)
    return GateEvidence(store, run, expected_revision, resolver)
