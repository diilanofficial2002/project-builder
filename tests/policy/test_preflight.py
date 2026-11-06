"""All HTTP is synthetic; never probe forbidden writes on real repositories."""

import httpx
import pytest


def inspect(api, repo, identity, http_case):
    inspector = api.github_inspector.GitHubInspector(transport=http_case.transport, token="synthetic-test-token")
    with api.preflight.use_inspector(inspector):
        return api.preflight.inspect_enforcement(repo, identity)


def test_preflight_only_uses_read_apis(api, repo, identity, http_case):
    report = inspect(api, repo, identity, http_case)
    assert http_case.requests
    assert all(r.method == "GET" and r.url.host == "api.github.com" for r in http_case.requests)
    assert report.mode == "LOCAL_ONLY"
    assert "CREDENTIAL_CONTAINMENT_UNVERIFIED" in report.reasons
    assert "ACTOR_UPDATE_MERGE_UNVERIFIED" in report.reasons
    assert report.repo == repo and report.actor_id == 7
    assert dict(report.refs)["main"] == "c" * 40
    assert (report.expires_at - report.checked_at).total_seconds() <= 300


def test_no_configured_credentials_never_uses_ambient_auth(api, repo, identity):
    report = api.preflight.inspect_enforcement(repo, identity)
    assert report.mode == "LOCAL_ONLY"
    assert "CREDENTIAL_UNAVAILABLE" in report.reasons


@pytest.mark.parametrize("path,value,reason", [
    ("/user", {"id": 99, "login": "worker"}, "IDENTITY_MISMATCH"),
    ("/repos/owner/sample", {"id": 99, "full_name": "owner/sample"}, "REPOSITORY_MISMATCH"),
    ("/repos/owner/sample/rulesets/12", {"id": 12, "enforcement": "evaluate", "bypass_actors": []}, "RULES_NOT_ENFORCED"),
    ("/repos/owner/sample/rulesets/12", {"id": 12, "enforcement": "active", "bypass_actors": [{"actor_type": "Team", "actor_id": 12, "bypass_mode": "always"}]}, "BYPASS_MEMBERSHIP_UNVERIFIED"),
    ("/repos/owner/sample/rulesets/12", {"id": 12, "enforcement": "active"}, "BYPASS_UNKNOWN"),
    ("/repos/owner/sample/contents/.github/workflows", (403, {}), "READ_UNAVAILABLE"),
])
def test_unknown_identity_bypass_or_workflow_is_local_only(api, repo, identity, http_case, path, value, reason):
    http_case.responses[path] = value
    report = inspect(api, repo, identity, http_case)
    assert report.mode == "LOCAL_ONLY"
    assert reason in report.reasons


@pytest.mark.parametrize("remote", ["https://evil.test/owner/sample.git", "https://github.com/other/sample.git",
    "https://github.com@evil.test/owner/sample.git", "https://github.com:444/owner/sample.git",
    "https://github.com/owner/sample.git?x=y", "file:///repo", "ssh://evil.test/owner/sample.git"])
def test_out_of_scope_remote_is_rejected(api, remote):
    with pytest.raises(ValueError):
        api.models.RepositoryRef(project_id="p", repository_id=42, owner="owner", name="sample", remote_url=remote)


def test_redirect_is_never_followed(api, repo, identity, http_case):
    http_case.responses["/repos/owner/sample"] = httpx.Response(302, headers={"Location": "https://evil.test/token"})
    report = inspect(api, repo, identity, http_case)
    assert report.mode == "LOCAL_ONLY" and "REDIRECT_REJECTED" in report.reasons
    assert len(http_case.requests) == 1


def test_cross_host_pagination_is_never_followed(api, repo, identity, http_case):
    http_case.responses["/repos/owner/sample/branches"] = httpx.Response(200, json=[],
        headers={"Link": '<https://evil.test/collect>; rel="next"'})
    report = inspect(api, repo, identity, http_case)
    assert "PAGINATION_REJECTED" in report.reasons
    assert all(r.url.host == "api.github.com" for r in http_case.requests)


def test_page_budget_and_response_size_fail_closed(api, repo, identity, http_case):
    http_case.responses["/repos/owner/sample/branches"] = httpx.Response(200, json=[],
        headers={"Link": '<https://api.github.com/repos/owner/sample/branches?page=2>; rel="next"'})
    report = inspect(api, repo, identity, http_case)
    assert "PAGE_LIMIT" in report.reasons
    assert len(http_case.requests) <= 8
    http_case.responses["/repos/owner/sample"] = httpx.Response(200, content=b"x" * 1_048_577)
    report = inspect(api, repo, identity, http_case)
    assert "RESPONSE_TOO_LARGE" in report.reasons


def test_workflow_executable_dependencies_are_never_certified(api, repo, identity, http_case):
    import base64
    http_case.responses["/repos/owner/sample/contents/.github/workflows"] = [
        {"type": "file", "path": ".github/workflows/build.yml", "name": "build.yml"}]
    http_case.responses["/repos/owner/sample/contents/.github/workflows/build.yml"] = {
        "type": "file", "encoding": "base64", "content": base64.b64encode(b"on: push\njobs:\n  run:\n    uses: foreign/repo/.github/workflows/deploy.yml@main").decode()}
    report = inspect(api, repo, identity, http_case)
    assert "WORKFLOW_EXECUTION_UNVERIFIED" in report.reasons
    assert report.mode == "LOCAL_ONLY"


def test_config_and_ref_changes_change_observation_digests(api, repo, identity, http_case):
    first = inspect(api, repo, identity, http_case)
    http_case.responses["/repos/owner/sample/branches"][0]["commit"]["sha"] = "f" * 40
    http_case.responses["/repos/owner/sample/rulesets/12"]["bypass_actors"] = [{"actor_type": "Integration", "actor_id": 3, "bypass_mode": "always"}]
    second = inspect(api, repo, identity, http_case)
    assert first.refs_digest != second.refs_digest
    assert first.rules_digest != second.rules_digest
    assert first.workflows_digest != second.workflows_digest


def test_same_host_foreign_repository_pagination_rejected(api, repo, identity, http_case):
    http_case.responses["/repos/owner/sample/branches"] = httpx.Response(200, json=[],
        headers={"Link": '<https://api.github.com/repos/other/repo/branches?page=2>; rel="next"'})
    assert "PAGINATION_REJECTED" in inspect(api, repo, identity, http_case).reasons
    assert not any("/other/" in r.url.path for r in http_case.requests)


@pytest.mark.parametrize("value", [None, "bad", {"unexpected": "shape"}])
def test_malformed_branch_data_fails_closed(api, repo, identity, http_case, value):
    http_case.responses["/repos/owner/sample/branches"] = value
    report = inspect(api, repo, identity, http_case)
    assert report.mode == "LOCAL_ONLY" and "MALFORMED_RESPONSE" in report.reasons


def test_transport_exception_is_sanitized(api, repo, identity):
    def handler(request):
        raise httpx.ReadTimeout("secret-token")
    inspector = api.github_inspector.GitHubInspector(transport=httpx.MockTransport(handler), token="secret-token")
    report = inspector.inspect_enforcement(repo, identity)
    assert "READ_UNAVAILABLE" in report.reasons
    assert "secret-token" not in str(report) and "secret-token" not in repr(inspector)


@pytest.mark.parametrize("raw_value", [b"1e400", b"-1e400", b"NaN", b"Infinity", b"-Infinity", b'"\\ud800"'])
def test_uncanonical_json_observations_return_malformed_report(api, repo, identity, http_case, raw_value):
    # json= would reject these values in the fake itself; exercise actual response decoding.
    body = b'{"id":42,"full_name":"owner/sample","permissions":{"push":' + raw_value + b'}}'
    http_case.responses["/repos/owner/sample"] = httpx.Response(200, content=body)
    report = inspect(api, repo, identity, http_case)
    assert report.mode == "LOCAL_ONLY"
    assert "MALFORMED_RESPONSE" in report.reasons
    assert len(http_case.requests) == 1
