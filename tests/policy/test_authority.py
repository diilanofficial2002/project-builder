"""Ceiling, routing, persisted bindings, and authenticated runtime authority."""

from datetime import datetime, timedelta, timezone

import pytest


@pytest.mark.parametrize("kind", ["merge_staging", "push_main", "push_staging", "open_pr_main",
    "enable_auto_merge", "enqueue_merge", "deploy_prod", "edit_protection", "delete_main", "delete_staging"])
def test_ceiling_cannot_be_overridden(api, policy_case, kind):
    c = policy_case
    result = api.authority.authorize(c.action(kind), c.contract, c.proof, c.evidence)
    assert not result.allowed
    assert result.code == "AUTHORITY_CEILING"


@pytest.mark.parametrize("kind,target", [("commit", "main"), ("integrate_stage", "staging"),
    ("create_feature", "refs/heads/main"), ("open_pr_develop", "staging"),
    ("open_pr_staging", "main"), ("delete_feature", "refs/heads/staging"),
    ("start_process", "main"), ("commit", "refs/tags/main"), ("commit", "HEAD"),
    ("commit", "feature/x:main"), ("commit", "main^{}")])
def test_benign_name_cannot_hide_protected_or_ambiguous_target(api, policy_case, kind, target):
    c = policy_case
    result = api.authority.authorize(c.action(kind, target=target), c.contract, c.proof, c.evidence)
    assert not result.allowed
    assert result.code in {"PROTECTED_REF", "INVALID_ROUTE"}


@pytest.mark.parametrize("kind,source,target", [("create_stage", "main", "stage/poc"),
    ("create_feature", "develop", "feature/work"), ("integrate_feature", "feature/work", "develop"),
    ("integrate_stage", "feature/work", "develop"), ("open_pr_staging", "feature/work", "staging")])
def test_ref_relationships_are_checked(api, policy_case, kind, source, target):
    c = policy_case
    result = api.authority.authorize(c.action(kind, source, target), c.contract, c.proof, c.evidence)
    assert not result.allowed
    assert result.code in {"INVALID_ROUTE", "PROTECTED_REF"}


def test_authenticated_runtime_can_authorize_ceiling_pr(api, policy_case):
    c = policy_case
    assert api.authority.authorize(c.action(), c.contract, c.proof, c.evidence).allowed


def test_caller_verified_mode_and_persisted_rows_are_not_authority(api, policy_case):
    c = policy_case
    untrusted = api.models.load_gate_evidence(c.store, c.run, c.snapshot.revision)
    assert api.authority.authorize(c.action(), c.contract, c.proof, untrusted).code == "UNVERIFIED_EVIDENCE"


@pytest.mark.parametrize("field,value", [("state_revision", 99), ("actor_id", 8),
    ("contract_digest", "foreign"), ("proof_digest", "foreign"), ("refs_digest", "changed"),
    ("rules_digest", "changed"), ("workflows_digest", "changed"), ("approval_receipt_id", "foreign"),
    ("evidence_digests", ()), ("evidence_digests", (("gate-1", "tampered"),)), ("build_digest", "other")])
def test_stale_or_foreign_bindings_deny(api, policy_case, field, value):
    from dataclasses import replace
    c = policy_case
    c.resolver.binding = replace(c.resolver.binding, **{field: value})
    assert not api.authority.authorize(c.action(), c.contract, c.proof, c.evidence).allowed


def test_state_is_reloaded_before_authorization(api, policy_case):
    c = policy_case
    c.store.compare_and_set(c.run, c.snapshot.revision, {"pending_changes": ["new"]})
    assert api.authority.authorize(c.action(), c.contract, c.proof, c.evidence).code == "STALE_STATE"


def test_contract_allowed_actions_cannot_bypass_approval_or_contract_binding(api, policy_case):
    c = policy_case
    changed = c.contract.model_copy(update={"approved_receipt_id": None})
    assert not api.authority.authorize(c.action(), changed, c.proof, c.evidence).allowed


@pytest.mark.parametrize("delta,ttl", [(-301, 300), (30, 300), (-10, 301)])
def test_freshness_cannot_be_extended_by_a_trusted_binding(api, policy_case, delta, ttl):
    from dataclasses import replace
    c = policy_case
    checked = datetime.now(timezone.utc) + timedelta(seconds=delta)
    proof = c.proof.model_copy(update={"checked_at": checked, "expires_at": checked + timedelta(seconds=ttl)})
    c.resolver.binding = replace(c.resolver.binding, proof_digest=api.models.report_digest(proof))
    assert api.authority.authorize(c.action(), c.contract, proof, c.evidence).code == "STALE_PROOF"


def test_changed_expected_sha_denies_remote_mutation(api, policy_case):
    c = policy_case
    assert not api.authority.authorize(c.action(expected_sha="f" * 40), c.contract, c.proof, c.evidence).allowed


@pytest.mark.parametrize("kind", ["stop_process", "cleanup_owned"])
def test_owned_resource_cleanup_remains_available_without_remote_proof(api, policy_case, kind):
    c = policy_case
    evidence = api.models.load_gate_evidence(c.store, c.run, c.snapshot.revision)
    proof = c.proof.model_copy(update={"mode": "LOCAL_ONLY"})
    result = api.authority.authorize(c.action(kind, None, None, expected_sha=None), c.contract, proof, evidence)
    assert result.allowed
    assert result.code == "REQUIRES_OWNERSHIP_CHECK"


def test_bootstrap_never_overwrites_existing_protected_ref(api, policy_case):
    c = policy_case
    assert api.authority.authorize(c.action("bootstrap_ref", None, "main", expected_sha=None),
        c.contract, c.proof, c.evidence).code == "REF_EXISTS"


def test_bootstrap_missing_ref_is_create_only(api, policy_case):
    from dataclasses import replace
    c = policy_case
    refs = tuple(pair for pair in c.proof.refs if pair[0] != "main")
    proof = c.proof.model_copy(update={"refs": refs, "refs_digest": api.models.digest_refs(refs)})
    c.resolver.binding = replace(c.resolver.binding, refs_digest=proof.refs_digest,
        proof_digest=api.models.report_digest(proof))
    result = api.authority.authorize(c.action("bootstrap_ref", None, "main", expected_sha=None),
        c.contract, proof, c.evidence)
    assert result.allowed
    assert result.code == "CREATE_ONLY"


@pytest.mark.parametrize("kind,source,target", [("setup_environment", None, None), ("bootstrap_ref", None, "main")])
def test_state_change_during_resolver_cannot_authorize_early_return(api, policy_case, kind, source, target):
    from dataclasses import replace
    c = policy_case
    refs = tuple(pair for pair in c.proof.refs if pair[0] != "main")
    proof = c.proof.model_copy(update={"refs": refs, "refs_digest": api.models.digest_refs(refs)})
    c.resolver.binding = replace(c.resolver.binding, refs_digest=proof.refs_digest,
        proof_digest=api.models.report_digest(proof))
    def resolve(**kwargs):
        c.store.compare_and_set(c.run, c.snapshot.revision, {"pending_changes": ["changed during resolution"]})
        return c.resolver.binding
    c.resolver.resolve = resolve
    result = api.authority.authorize(c.action(kind, source, target, expected_sha=None), c.contract, proof, c.evidence)
    assert not result.allowed
    assert result.code == "STALE_STATE"


def test_missing_persisted_evidence_denies_even_with_trusted_binding(api, policy_case):
    c = policy_case
    snapshot = c.store.compare_and_set(c.run, c.snapshot.revision, {"evidence_ids": ["absent"]})
    evidence = api.models.load_gate_evidence(c.store, c.run, snapshot.revision, resolver=c.resolver)
    assert api.authority.authorize(c.action(), c.contract, c.proof, evidence).code == "MISSING_EVIDENCE"


def test_foreign_repository_binding_denies(api, policy_case):
    from dataclasses import replace
    c = policy_case
    c.resolver.binding = replace(c.resolver.binding, repo=c.proof.repo.model_copy(update={"repository_id": 99}))
    assert not api.authority.authorize(c.action(), c.contract, c.proof, c.evidence).allowed


def test_resolver_failure_never_exposes_secret_or_grants_authority(api, policy_case):
    c = policy_case
    def resolve(**kwargs):
        raise RuntimeError("secret-token")
    c.resolver.resolve = resolve
    result = api.authority.authorize(c.action(), c.contract, c.proof, c.evidence)
    assert not result.allowed
    assert "secret-token" not in str(result)


def test_local_only_proof_denies_remote_action(api, policy_case):
    c = policy_case
    assert api.authority.authorize(c.action(), c.contract,
        c.proof.model_copy(update={"mode": "LOCAL_ONLY"}), c.evidence).code == "LOCAL_ONLY"


def test_foreign_run_action_denied(api, policy_case):
    c = policy_case
    assert api.authority.authorize(c.action(run_id="foreign"), c.contract, c.proof, c.evidence).code == "CONTRACT_MISMATCH"
