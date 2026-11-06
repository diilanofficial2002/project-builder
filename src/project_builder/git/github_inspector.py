"""Bounded GitHub GET observations, never a certification of ambient credentials.

Only an explicitly supplied credential is used. There is no write transport,
shell fallback, redirect following, or workflow execution. Generic GitHub APIs
cannot prove host credential containment, so this inspector returns LOCAL_ONLY.
"""

import base64
import re
import time
from datetime import datetime, timedelta, timezone
from urllib.parse import parse_qs, quote, urlsplit

import httpx
from pydantic import SecretStr

from project_builder.policy.models import EnforcementReport, RemoteIdentity, RepositoryRef, digest_data, digest_refs


class _InspectionFailure(Exception):
    pass


class _Reader:
    def __init__(self, client: httpx.Client):
        self.client = client
        self.deadline = time.monotonic() + 30
        self.requests = 0

    def get(self, path: str, *, missing_ok: bool = False) -> tuple[object, str | None]:
        if self.requests >= 100 or time.monotonic() >= self.deadline:
            raise _InspectionFailure("REQUEST_BUDGET")
        self.requests += 1
        # Paths are generated locally. No response-provided URLs reach this call.
        with self.client.stream("GET", "https://api.github.com" + path) as response:
            if response.is_redirect:
                raise _InspectionFailure("REDIRECT_REJECTED")
            if response.status_code == 404 and missing_ok:
                return None, None
            if response.status_code != 200:
                raise _InspectionFailure("READ_UNAVAILABLE")
            content = bytearray()
            for chunk in response.iter_bytes():
                content.extend(chunk)
                if len(content) > 1_048_576:
                    raise _InspectionFailure("RESPONSE_TOO_LARGE")
                if time.monotonic() >= self.deadline:
                    raise _InspectionFailure("REQUEST_BUDGET")
            import json
            data = json.loads(content)
            return data, response.headers.get("link")

    def listing(self, path: str) -> list:
        result = []
        for page in range(1, 6):
            separator = "&" if "?" in path else "?"
            data, link = self.get(f"{path}{separator}per_page=100&page={page}")
            if not isinstance(data, list) or len(data) > 100:
                raise _InspectionFailure("MALFORMED_RESPONSE")
            result.extend(data)
            if not link:
                return result
            links = httpx.Response(200, headers={"link": link}).links
            next_link = links.get("next")
            if next_link is None:
                return result
            url = urlsplit(next_link["url"])
            expected = urlsplit(path)
            params = parse_qs(url.query, strict_parsing=True)
            if (url.scheme != "https" or url.netloc != "api.github.com" or url.fragment or
                    url.path != expected.path or set(params) - {"page", "per_page", "includes_parents"} or
                    not re.fullmatch(r"[1-9][0-9]*", "".join(params.get("page", [])))):
                raise _InspectionFailure("PAGINATION_REJECTED")
            # Generate our own next page, never follow the response URL.
        raise _InspectionFailure("PAGE_LIMIT")


class GitHubInspector:
    """Owns one short-lived HTTP client per inspection; no global/environment auth.

    Inject httpx.BaseTransport for tests; token is explicit and never serialized.
    App installation identities unsupported by /user fail closed until a dedicated
    authenticated installation identity provider is implemented.
    """

    def __init__(self, *, transport: httpx.BaseTransport | None = None, token: str | None = None):
        self._transport = transport
        self._token = SecretStr(token) if token else None

    def inspect_enforcement(self, repo: RepositoryRef, identity: RemoteIdentity) -> EnforcementReport:
        repo = RepositoryRef.model_validate(repo.model_dump())
        identity = RemoteIdentity.model_validate(identity.model_dump())
        checked_at = datetime.now(timezone.utc)
        refs: tuple[tuple[str, str], ...] = ()
        rules: dict = {}
        workflows: dict = {}
        reasons = ["CREDENTIAL_CONTAINMENT_UNVERIFIED", "ACTOR_UPDATE_MERGE_UNVERIFIED",
                   "WORKFLOW_SIDE_EFFECTS_UNVERIFIED"]
        if self._token is None:
            reasons.append("CREDENTIAL_UNAVAILABLE")
        else:
            try:
                with httpx.Client(transport=self._transport, follow_redirects=False, trust_env=False,
                        timeout=httpx.Timeout(5), headers={"Accept": "application/vnd.github+json",
                            "X-GitHub-Api-Version": "2026-03-10",
                            "Authorization": "Bearer " + self._token.get_secret_value()}) as client:
                    reader = _Reader(client)
                    prefix = f"/repos/{repo.owner}/{repo.name}"
                    repository, _ = reader.get(prefix)
                    if (type(repository.get("id")) is not int or repository["id"] != repo.repository_id or
                        repository.get("full_name", "").casefold() != f"{repo.owner}/{repo.name}".casefold()):
                        raise _InspectionFailure("REPOSITORY_MISMATCH")
                    actor, _ = reader.get("/user")
                    if (type(actor.get("id")) is not int or actor["id"] != identity.actor_id or
                            actor.get("login") != identity.login):
                        raise _InspectionFailure("IDENTITY_MISMATCH")
                    rules["repository_permissions"] = repository.get("permissions")
                    if not isinstance(repository.get("permissions"), dict):
                        reasons.append("ACTOR_PERMISSIONS_UNKNOWN")
                    elif repository["permissions"].get("admin"):
                        reasons.append("ACTOR_ADMIN_PRIVILEGES")
                    branches = reader.listing(prefix + "/branches")
                    pairs = []
                    for branch in branches:
                        name, sha = branch["name"], branch["commit"]["sha"]
                        if (not isinstance(name, str) or not name or not isinstance(sha, str) or
                                not re.fullmatch(r"[0-9a-f]{40}|[0-9a-f]{64}", sha)):
                            raise _InspectionFailure("MALFORMED_RESPONSE")
                        pairs.append((name, sha))
                    if len(dict(pairs)) != len(pairs):
                        raise _InspectionFailure("INCONSISTENT_REFS")
                    refs = tuple(sorted(pairs))
                    for branch in ("main", "staging"):
                        rules[branch] = reader.listing(prefix + "/rules/branches/" + branch)
                        if not rules[branch]:
                            reasons.append("PROTECTION_MISSING")
                    rulesets = reader.listing(prefix + "/rulesets?includes_parents=true")
                    rules["rulesets"] = rulesets
                    details = []
                    rules["details"] = details
                    for ruleset in rulesets:
                        if ruleset.get("source_type") != "Repository" or ruleset.get("source") != f"{repo.owner}/{repo.name}":
                            reasons.append("BYPASS_UNKNOWN")
                            continue
                        id = ruleset.get("id")
                        if type(id) is not int or id < 1:
                            raise _InspectionFailure("MALFORMED_RESPONSE")
                        detail, _ = reader.get(prefix + f"/rulesets/{id}")
                        details.append(detail)
                        if detail.get("enforcement") != "active":
                            reasons.append("RULES_NOT_ENFORCED")
                        bypass = detail.get("bypass_actors")
                        if not isinstance(bypass, list):
                            reasons.append("BYPASS_UNKNOWN")
                        elif bypass:
                            # No assumptions about user, app, team or role memberships.
                            reasons.append("BYPASS_MEMBERSHIP_UNVERIFIED")
                    for name, sha in refs:
                        entries, _ = reader.get(prefix + "/contents/.github/workflows?ref=" + sha, missing_ok=True)
                        workflows[name] = {"sha": sha, "entries": entries, "files": []}
                        if entries is None:
                            continue
                        if not isinstance(entries, list) or len(entries) > 100:
                            raise _InspectionFailure("MALFORMED_RESPONSE")
                        for entry in entries:
                            path = entry.get("path", "")
                            if (entry.get("type") != "file" or not re.fullmatch(
                                    r"\.github/workflows/[A-Za-z0-9_.-]+\.ya?ml", path)):
                                reasons.append("WORKFLOW_EXECUTION_UNVERIFIED")
                                continue
                            content, _ = reader.get(prefix + "/contents/" + quote(path, safe="/") + "?ref=" + sha)
                            if content.get("encoding") != "base64" or not isinstance(content.get("content"), str):
                                raise _InspectionFailure("MALFORMED_RESPONSE")
                            source = base64.b64decode("".join(content["content"].split()), validate=True)
                            workflows[name]["files"].append({"path": path, "content_digest": digest_data(source.hex())})
                            # Arbitrary shell, external actions and reusable workflows cannot
                            # be certified by parsing YAML. Never execute or trust their claims.
                            reasons.append("WORKFLOW_EXECUTION_UNVERIFIED")
            except _InspectionFailure as error:
                reasons.append(str(error))
            except httpx.HTTPError:
                reasons.append("READ_UNAVAILABLE")
            except (ValueError, TypeError, KeyError, AttributeError):
                reasons.append("MALFORMED_RESPONSE")
        return EnforcementReport(mode="LOCAL_ONLY", repo=repo, actor_id=identity.actor_id,
            refs_digest=digest_refs(refs), rules_digest=digest_data(rules), workflows_digest=digest_data(workflows),
            checked_at=checked_at, expires_at=checked_at + timedelta(seconds=300),
            reasons=tuple(dict.fromkeys(reasons)), refs=refs)
