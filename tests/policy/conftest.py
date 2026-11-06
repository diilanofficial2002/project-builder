"""Synthetic policy/HTTP fixtures; trusted providers here are test-only."""

import importlib
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from typing import get_args

import httpx
import pytest

from project_builder.contracts import ActionKind, ActionRequest, StageContract
from project_builder.state.models import EvidenceRef
from project_builder.state.store import StateStore


@pytest.fixture
def api():
    modules = {}
    for name in ("policy.models", "policy.authority", "policy.preflight", "git.github_inspector"):
        try:
            modules[name.rsplit(".", 1)[1]] = importlib.import_module("project_builder." + name)
        except ModuleNotFoundError as error:
            if error.name.startswith("project_builder.policy") or error.name.startswith("project_builder.git"):
                pytest.fail("Task 3 authority/preflight interface is not implemented")
            raise
    return SimpleNamespace(**modules)


@pytest.fixture
def repo(api):
    return api.models.RepositoryRef(project_id="test-project", repository_id=42,
        owner="owner", name="sample", remote_url="https://github.com/owner/sample.git")


@pytest.fixture
def identity(api):
    return api.models.RemoteIdentity(actor_id=7, login="worker")


@pytest.fixture
def policy_case(api, repo, identity, raw_contract, tmp_path):
    contract = StageContract(**(raw_contract | {"allowed_actions": frozenset(get_args(ActionKind)),
        "approved_receipt_id": "approval-1"}))
    with StateStore(tmp_path / "state.sqlite3") as store:
        run = store.create_run(contract)
        snapshot = store.read_run(run)
        reference = store.record_evidence(EvidenceRef(id="gate-1", kind="gate",
            producer_id="synthetic-provider", build_digest="build-1", contract_digest=snapshot.contract_digest,
            content_digest="content-1", observed_at=datetime.now(timezone.utc), provenance="automated-test"))
        snapshot = store.compare_and_set(run, 1, {"evidence_ids": [reference.id]})
        now = datetime.now(timezone.utc)
        refs = (("develop", "a" * 40), ("staging", "b" * 40), ("main", "c" * 40),
                ("stage/poc", "d" * 40), ("feature/work", "e" * 40))
        proof = api.models.EnforcementReport(mode="VERIFIED", repo=repo, actor_id=7,
            refs_digest=api.models.digest_refs(refs), rules_digest="rules-1", workflows_digest="workflows-1",
            checked_at=now, expires_at=now + timedelta(seconds=300), reasons=(), refs=refs)
        binding = api.models.VerifiedBindings(repo=repo, actor_id=7,
            state_revision=snapshot.revision, contract_digest=snapshot.contract_digest,
            refs_digest=proof.refs_digest, rules_digest=proof.rules_digest, workflows_digest=proof.workflows_digest,
            proof_digest=api.models.report_digest(proof), approval_receipt_id="approval-1",
            evidence_digests=((reference.id, reference.content_digest),), build_digest="build-1")

        class TestOnlyResolver:
            def resolve(self, **kwargs):
                return self.binding

        resolver = TestOnlyResolver()
        resolver.binding = binding
        evidence = api.models.load_gate_evidence(store, run, snapshot.revision, resolver=resolver)
        def action(kind="open_pr_staging", source="develop", target="staging", **changes):
            return ActionRequest(**(dict(kind=kind, project_id=run.project_id, run_id=run.run_id,
                source_ref=source, target_ref=target, expected_sha="a" * 40, operation_id="operation-1") | changes))
        yield SimpleNamespace(contract=contract, store=store, run=run, snapshot=snapshot,
            proof=proof, resolver=resolver, evidence=evidence, action=action, reference=reference)


@pytest.fixture
def http_case():
    responses = {
        "/repos/owner/sample": {"id": 42, "full_name": "owner/sample", "permissions": {"admin": False, "push": True, "pull": True}},
        "/user": {"id": 7, "login": "worker"},
        "/repos/owner/sample/branches": [
            {"name": name, "commit": {"sha": char * 40}, "protected": True}
            for name, char in (("main", "c"), ("staging", "b"), ("develop", "a"))],
        "/repos/owner/sample/rules/branches/main": [{"type": "pull_request", "ruleset_id": 12}],
        "/repos/owner/sample/rules/branches/staging": [{"type": "pull_request", "ruleset_id": 12}],
        "/repos/owner/sample/rulesets": [{"id": 12, "source_type": "Repository", "source": "owner/sample", "enforcement": "active"}],
        "/repos/owner/sample/rulesets/12": {"id": 12, "enforcement": "active", "bypass_actors": [], "rules": [{"type": "pull_request"}]},
        "/repos/owner/sample/contents/.github/workflows": (404, {}),
    }
    requests = []
    def handler(request):
        requests.append(request)
        value = responses.get(request.url.path, (404, {}))
        if isinstance(value, httpx.Response):
            return value
        status, body = value if isinstance(value, tuple) else (200, value)
        return httpx.Response(status, json=body)
    return SimpleNamespace(responses=responses, requests=requests, transport=httpx.MockTransport(handler))
