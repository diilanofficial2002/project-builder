"""Immutable local ceiling. This does not constrain raw host credentials/tools.

Every allowed result is a precondition, not an executable capability. Git callers
must refresh immediately before mutation, bind exact refs/SHAs, and perform CAS
or create-only operations. T4 must verify resource ownership for cleanup results.
"""

import re
from datetime import datetime, timezone
from typing import Final

from project_builder.contracts import ActionDecision, ActionRequest, StageContract
from project_builder.policy.models import EnforcementReport, GateEvidence, digest_refs, report_digest

DENIED_OPERATIONS: Final = frozenset({"merge_staging", "push_main", "push_staging", "open_pr_main",
    "enable_auto_merge", "enqueue_merge", "deploy_prod", "edit_protection", "delete_main", "delete_staging"})
PROTECTED_REFS: Final = frozenset({"main", "staging"})
LOCAL_RESOURCE_ACTIONS: Final = frozenset({"start_process", "stop_process", "cleanup_owned",
    "setup_environment", "install_project_tool"})


def _decision(code: str, allowed: bool = False) -> ActionDecision:
    return ActionDecision(allowed=allowed, code=code, reasons=[code])


def _branch(ref: str | None) -> str | None:
    if ref is None:
        return None
    ref = ref.removeprefix("refs/heads/")
    if (not re.fullmatch(r"[A-Za-z0-9_][A-Za-z0-9_./-]*", ref) or
        ref.startswith("refs/") or ref in {"HEAD", "FETCH_HEAD", "ORIG_HEAD"} or
        ".." in ref or "//" in ref or any(p.startswith(".") or p.endswith((".", ".lock")) for p in ref.split("/")) or
        ref.endswith("/")):
        raise ValueError("ambiguous branch")
    return ref


def _route(kind: str, source: str | None, target: str | None) -> bool:
    stage = lambda ref: bool(ref and ref.startswith("stage/") and len(ref) > 6)
    feature = lambda ref: bool(ref and ref.startswith("feature/") and len(ref) > 8)
    if kind in LOCAL_RESOURCE_ACTIONS:
        return source is None and target is None
    if kind == "bootstrap_ref":
        return source is None and target in {"main", "staging", "develop"}
    if kind == "create_stage":
        return source == "develop" and stage(target)
    if kind == "create_feature":
        return stage(source) and feature(target)
    if kind in {"integrate_feature", "open_pr_stage"}:
        return feature(source) and stage(target)
    if kind in {"integrate_stage", "open_pr_develop"}:
        return stage(source) and target == "develop"
    if kind == "open_pr_staging":
        return source == "develop" and target == "staging"
    if kind == "delete_feature":
        return source is None and feature(target)
    if kind == "commit":
        return source is None and feature(target)
    return False


def authorize(action: ActionRequest, contract: StageContract, proof: EnforcementReport,
              evidence: GateEvidence) -> ActionDecision:
    # Ceiling precedes every approval, proof, configured allow-list and resolver.
    if action.kind in DENIED_OPERATIONS:
        return _decision("AUTHORITY_CEILING")
    try:
        action = ActionRequest.model_validate(action.model_dump())
        source, target = _branch(action.source_ref), _branch(action.target_ref)
    except (ValueError, TypeError, AttributeError):
        return _decision("INVALID_ROUTE")
    if target in PROTECTED_REFS and not (action.kind == "bootstrap_ref" or
            action.kind == "open_pr_staging" and target == "staging" and source == "develop"):
        return _decision("PROTECTED_REF")
    if not _route(action.kind, source, target):
        return _decision("INVALID_ROUTE")
    try:
        contract = StageContract.model_validate(contract.model_dump())
        snapshot = evidence.store.read_run(evidence.run)
        stored_contract = evidence.store.read_contract(evidence.run)
    except (ValueError, LookupError, AttributeError):
        return _decision("UNVERIFIED_EVIDENCE")
    if (action.project_id != contract.project_id or action.project_id != evidence.run.project_id or
            action.run_id != evidence.run.run_id or contract != stored_contract):
        return _decision("CONTRACT_MISMATCH")
    if snapshot.revision != evidence.expected_revision:
        return _decision("STALE_STATE")
    if action.kind in {"stop_process", "cleanup_owned"}:
        return _decision("REQUIRES_OWNERSHIP_CHECK", True)
    if action.kind not in contract.allowed_actions:
        return _decision("ACTION_NOT_APPROVED")
    if evidence.resolver is None or not contract.approved_receipt_id:
        return _decision("UNVERIFIED_EVIDENCE")
    try:
        proof = EnforcementReport.model_validate(proof.model_dump())
        references = tuple(evidence.store.read_evidence(id) for id in snapshot.evidence_ids)
        if not references or any(ref is None for ref in references):
            return _decision("MISSING_EVIDENCE")
        binding = evidence.resolver.resolve(run=evidence.run, action=action,
            contract_digest=snapshot.contract_digest, proof=proof, references=references)
    except Exception:
        # No exception text: a resolver may contain credentials or private paths.
        return _decision("UNVERIFIED_EVIDENCE")
    if binding is None:
        return _decision("UNVERIFIED_EVIDENCE")
    if (binding.state_revision != snapshot.revision or binding.contract_digest != snapshot.contract_digest or
        binding.approval_receipt_id != contract.approved_receipt_id or binding.repo.project_id != action.project_id):
        return _decision("EVIDENCE_BINDING_MISMATCH")
    actual = {ref.id: ref for ref in references}
    if not binding.evidence_digests or len(dict(binding.evidence_digests)) != len(binding.evidence_digests):
        return _decision("MISSING_EVIDENCE")
    for id, digest in binding.evidence_digests:
        ref = actual.get(id)
        if (ref is None or ref.content_digest != digest or ref.contract_digest != snapshot.contract_digest or
                ref.build_digest != binding.build_digest):
            return _decision("EVIDENCE_BINDING_MISMATCH")
    # Resolver I/O can race another writer; cover local and bootstrap paths too.
    # Callers still need atomic Git CAS and resource ownership checks.
    if evidence.store.read_run(evidence.run).revision != snapshot.revision:
        return _decision("STALE_STATE")
    if action.kind in LOCAL_RESOURCE_ACTIONS or action.kind == "commit":
        return _decision("LOCAL_ACTION", True)
    now = datetime.now(timezone.utc)
    if (not proof.checked_at <= now < proof.expires_at or
            not 0 < (proof.expires_at - proof.checked_at).total_seconds() <= 300):
        return _decision("STALE_PROOF")
    if proof.mode != "VERIFIED" or proof.reasons:
        return _decision("LOCAL_ONLY")
    if (binding.repo != proof.repo or binding.actor_id != proof.actor_id or
        binding.proof_digest != report_digest(proof) or binding.refs_digest != proof.refs_digest or
        binding.rules_digest != proof.rules_digest or binding.workflows_digest != proof.workflows_digest or
        digest_refs(proof.refs) != proof.refs_digest or len(dict(proof.refs)) != len(proof.refs)):
        return _decision("PROOF_BINDING_MISMATCH")
    refs = dict(proof.refs)
    if action.kind in {"bootstrap_ref", "create_stage", "create_feature"}:
        if target in refs:
            return _decision("REF_EXISTS")
        if action.kind == "bootstrap_ref":
            if action.expected_sha is not None:
                return _decision("CREATE_ONLY_REQUIRED")
            return _decision("CREATE_ONLY", True)
    expected_ref = target if action.kind == "delete_feature" else source
    if expected_ref is None or action.expected_sha is None or refs.get(expected_ref) != action.expected_sha:
        return _decision("REF_CHANGED")
    if action.kind not in {"create_stage", "create_feature"} and target not in refs:
        return _decision("REF_MISSING")
    return _decision("AUTHORIZED", True)
