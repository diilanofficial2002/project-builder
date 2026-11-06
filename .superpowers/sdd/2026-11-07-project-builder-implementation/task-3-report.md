# Task 3 report — immutable authority ceiling and read-only preflight

Status: DONE_WITH_CONCERNS (expected external enforcement/provider prerequisites remain unverified).

Implementation commit: `4f4f5337e8fee2c6be557f3a98867ea5581da458` (`feat: enforce immutable authority ceiling and remote preflight`). This report is committed separately so it can identify the implementation commit exactly.

Branch: `feature/pb-v0-1/poc/authority`; base: `48f75b160031e4fe20dc687515d4656026bdbe47`. No merge, push, deployment, live credential use, or forbidden-write probe was performed.

## Delivered behavior

- Code-owned forbidden operation set is evaluated before contracts, evidence or resolver calls. Adding a forbidden operation to `StageContract.allowed_actions` cannot grant it.
- Ref routing checks normalized explicit branch refs, rejecting protected targets, refspecs, symbolic refs, non-head namespaces, and invalid source/target relationships even under benign operation names. Routes are develop → stage/* → feature/* and feature/* → stage/* → develop; ceiling PR is develop → staging.
- Existing main/staging refs cannot be updated/deleted; bootstrap is a distinct missing-ref/create-only result. It requires `expected_sha=None`, authenticated remote prerequisites, and an absent destination. T12 must implement create-only Git operations, never an update fallback.
- Evidence is re-read from StateStore; run, current state revision, stored contract, approval ID, build digest, required evidence IDs/content digests, repository, actor, proof digest, refs/rules/workflow digests and <=300-second freshness are checked. A second revision read after resolver I/O covers bootstrap and local early-return paths as well as remote operations.
- A caller-created `VERIFIED` report or persisted evidence row does not grant authority. Without an internal trusted resolver, gated mutations deny. Stop/cleanup return `REQUIRES_OWNERSHIP_CHECK` without requiring approval or remote proof; T4 must still check actual resource ownership. Read-only status/help operations are outside ActionRequest's mutation policy and remain router concerns.
- The injectable inspector sends GET only to `https://api.github.com`. It checks the exact onboarded remote scope, numeric repository ID/full name, actor ID/login, repository permissions, branch refs, active branch rules, repository ruleset details/bypass data, and workflow directory/content observations pinned to branch SHAs.
- HTTP limits: no redirects/environment proxies/ambient auth; explicit token only; 5-second per-operation timeout, 30-second inspection budget checked across requests/chunks, max 100 requests, 5 pages per list, 100 entries per list page, 1 MiB per response. The next read may consume up to its bounded timeout after the overall deadline check. Pagination URLs are validated for host and original endpoint, then pages are generated locally instead of following returned URLs. Exceptions never copy token-bearing text into reports.
- Workflow source is hashed, never executed. No YAML parsing is used to claim arbitrary shell/external Actions/reusable workflows are safe. Unknown bypass membership and incomplete reads are explicit failures. Generic GitHub observations always remain `LOCAL_ONLY` because credential containment, actor update/merge restrictions and workflow side effects are not mechanically established.

## Exported APIs and integration contract

### `policy/authority.py`

`authorize(action: ActionRequest, contract: StageContract, proof: EnforcementReport, evidence: GateEvidence) -> ActionDecision`.

`DENIED_OPERATIONS`, `PROTECTED_REFS`, and `LOCAL_RESOURCE_ACTIONS` are frozen code constants, with no configuration overrides. An allowed result is a precondition, not a bearer capability or shell command. The host Python process is trusted; monkey-patching code or arbitrary execution in it is not sandboxed by these constants.

### `policy/models.py`

- `RepositoryRef`: frozen strict model with `project_id`, `repository_id` (positive GitHub numeric ID), `owner`, `name`, `remote_url`. Supported URLs are exact onboarded github.com HTTPS, git@github.com SCP form, or ssh://git@github.com form, with optional `.git`; no alternate hosts, credentials in HTTPS URL, ports, queries, or foreign repository paths. Supply this from trusted onboarding, not arbitrary remote input.
- `RemoteIdentity`: frozen strict model with positive `actor_id` and `login`. Current inspector uses `/user`; installation identities need a future dedicated identity adapter and currently fail closed.
- `EnforcementReport`: frozen strict model with `mode` (`LOCAL_ONLY`/`VERIFIED`), `repo`, `actor_id`, `refs_digest`, `rules_digest`, `workflows_digest`, timezone-aware `checked_at`/`expires_at`, tuple `reasons`, and tuple `refs` of `(branch_name, sha)`. Constructor validation is not proof authentication. `VERIFIED` is reserved for a future authenticated enforcement provider; this inspector never produces it.
- `digest_data(value)`, `digest_refs(refs)`, `report_digest(report)`: canonical SHA-256 helpers. Ref digest sorts pairs; report digest covers the full report, including repository, identity, timing, reasons and observation digests.
- `VerifiedBindings`: frozen INTERNAL dataclass with `repo`, `actor_id`, `state_revision`, `contract_digest`, `refs_digest`, `rules_digest`, `workflows_digest`, `proof_digest`, `approval_receipt_id`, `evidence_digests` (tuple of ID/content-digest pairs), `build_digest`. It is a result from trusted services, never an MCP request or model-produced attestation.
- `AuthorityResolver` protocol: `resolve(*, run: RunIdentity, action: ActionRequest, contract_digest: str, proof: EnforcementReport, references: tuple[EvidenceRef, ...]) -> VerifiedBindings | None`. Resolve freshly for the exact action/run. Authenticate the inspection receipt underlying `proof_digest`, refresh repo/actor/refs/config, verify approval channel/expiry/contract and action scope, evaluate every required gate, hash actual evidence artifacts, and return None for any unknown. Neither provenance strings nor persisted rows establish trust. No production resolver is supplied until trusted host/gate services exist.
- `GateEvidence`: frozen INTERNAL live handle with `store`, copied `run`, `expected_revision`, `resolver`. It carries no passed/approved booleans and is not a serializable command schema.
- `load_gate_evidence(store: StateStore, run: RunIdentity, expected_revision: int, *, resolver: AuthorityResolver | None = None) -> GateEvidence`. Checks identity/readability and positive revision; authorization re-reads the current snapshot/contract/evidence rather than trusting a cached list. Default resolver absence denies gated mutations. Do not deserialize or construct resolvers from tool payloads.

StateStore persistence is unchanged: T2 stores evidence metadata and explicitly does not authenticate producers or hash external artifacts. This task does not misrepresent stored `content_digest` as proof that external content was verified; that responsibility belongs to the authenticated resolver. Synthetic positive resolver implementations live only in tests.

### `policy/preflight.py` and `git/github_inspector.py`

- Exact facade: `inspect_enforcement(repo: RepositoryRef, identity: RemoteIdentity) -> EnforcementReport`.
- `use_inspector(inspector: GitHubInspector)` is a context manager using ContextVar for scoped service/test injection; it restores the prior inspector. No configured inspector means no credential and no network attempt.
- `GitHubInspector(*, transport: httpx.BaseTransport | None = None, token: str | None = None)`; `.inspect_enforcement(repo, identity)` performs observations using a short-lived owned HTTP client. Use injected fake transport for tests. Explicit token is retained as SecretStr and is not included in report/repr.

For T12: load GateEvidence with the trusted composition root's resolver immediately before mutation; refresh inspection and state/current config; bind the actual Git repository to RepositoryRef and exact normalized refs/SHAs. Reauthorize after config/ref/state changes. Policy's `expected_sha` is the source SHA for integration/PR/create operations and target SHA for feature deletion. Source is None for local feature commit/deletion and bootstrap; local commit routing targets feature/* only. Use full refs/heads names in the actual Git adapter, atomic compare-and-set on affected refs, create-only semantics for bootstrap/new branches, and the operation receipt/idempotency machinery. Do not map an allowed result to arbitrary shell or infer that process-wide raw Git credentials are restricted. Proof expiry is not permission to skip the immediate refresh/CAS.

For T5/T13/T15: implement the resolver from trusted approval/inspection/gate services. Its required evidence set must represent every gate for the specific action, scope and current build; policy validates all returned digests against current state rows but cannot decide missing future gate requirements itself. Bind action-specific approval and branch ownership inside the resolver; the core route grammar alone does not establish which feature belongs to which stage.

## Tests and exact terminal results

Environment: Windows, uv `0.11.20`, frozen project lock, isolated worktree `.venv`. Interpreter output:

```text
3.14.4 (tags/v3.14.4:23116f9, Apr  7 2026, 14:10:54) [MSC v.1944 64 bit (AMD64)]
C:\Users\bakao\.codex\worktrees\project-builder-poc\project-builder\.venv\Scripts\python.exe
```

Tests were written before implementation. Initial command `uv run --frozen --python 3.14.4 pytest tests/policy -q --tb=short` exited 1 because this task's modules did not exist. Representative exact diagnostic and final summary:

```text
E   ModuleNotFoundError: No module named 'project_builder.policy'
E   Failed: Task 3 authority/preflight interface is not implemented
69 errors in 0.73s
```

These were missing task-owned interfaces, not unrelated dependency failures. After implementation, the first run had one test expecting INVALID_ROUTE where the stronger protected-target check correctly returned PROTECTED_REF; the test was corrected to assert denial with either valid reason. First focused GREEN:

```text
.....................................................................    [100%]
69 passed in 0.95s
```

Self-review added regression tests before fixing the stale-state early-return issue. Exact behavioral RED command: `uv run --frozen --python 3.14.4 pytest tests/policy -q --tb=short` (exit 1):

```text
.................................................FF..................... [ 88%]
.........                                                                [100%]
================================== FAILURES ===================================
_ test_state_change_during_resolver_cannot_authorize_early_return[setup_environment-None-None] _
tests\policy\test_authority.py:130: in test_state_change_during_resolver_cannot_authorize_early_return
    assert not result.allowed
E   AssertionError: assert not True
E    +  where True = ActionDecision(allowed=True, code='LOCAL_ACTION', reasons=['LOCAL_ACTION']).allowed
_ test_state_change_during_resolver_cannot_authorize_early_return[bootstrap_ref-None-main] _
tests\policy\test_authority.py:130: in test_state_change_during_resolver_cannot_authorize_early_return
    assert not result.allowed
E   AssertionError: assert not True
E    +  where True = ActionDecision(allowed=True, code='CREATE_ONLY', reasons=['CREATE_ONLY']).allowed
=========================== short test summary info ===========================
FAILED tests/policy/test_authority.py::test_state_change_during_resolver_cannot_authorize_early_return[setup_environment-None-None]
FAILED tests/policy/test_authority.py::test_state_change_during_resolver_cannot_authorize_early_return[bootstrap_ref-None-main]
2 failed, 79 passed in 1.25s
```

Moved the post-resolver state revision check before every allowed return. Final focused GREEN, `uv run --frozen --python 3.14.4 pytest tests/policy -q` (exit 0):

```text
........................................................................ [ 88%]
.........                                                                [100%]
81 passed in 1.07s
```

Full suite once after final code changes, `uv run --frozen --python 3.14.4 pytest -q` (exit 0):

```text
........................................................................ [ 37%]
........................................................................ [ 75%]
................................................                         [100%]
192 passed in 2.63s
```

`git diff --cached --check` passed with no output before implementation commit. Git emitted only the workspace's expected LF→CRLF conversion warnings while adding new files; pytest had no warnings. Tests use fake HTTP transport and real isolated StateStore databases. No synthetic fixture is represented as human/native/external enforcement evidence.

## Files

- `src/project_builder/policy/models.py`
- `src/project_builder/policy/authority.py`
- `src/project_builder/policy/preflight.py`
- `src/project_builder/git/github_inspector.py`
- `tests/policy/conftest.py`
- `tests/policy/test_authority.py`
- `tests/policy/test_preflight.py`
- `.superpowers/sdd/2026-11-07-project-builder-implementation/task-3-report.md`

## Self-review, concerns and honest verification limits

- Reviewed denial precedence, benign-name protected targeting, foreign/missing/stale state/evidence/build/repo/actor bindings, bounded bootstrap, expected SHA, report TTL, resolver exception sanitization, redirects/cross-host and cross-repo pagination, response/page limits, malformed reads, workflow execution and config digest changes. The stale-state defect found during review is covered by the explicit RED/GREEN regression above.
- Generic GitHub GET responses are observational only. A rules digest covers collected permissions/active branch rules/repository rulesets; it is not certification of every classic, inherited organization/enterprise or external enforcement configuration. Inherited bypass membership, arbitrary workflows, external side effects and raw host credential containment remain unproven. No production VERIFIED proof/provider was invented.
- Current production remote actions therefore remain LOCAL_ONLY/denied. This is the controller-approved boundary, not a blocker to implementing subsequent tasks. A future enforced credential/host boundary must be authenticated and observed; an add-on, prompt, DTO or self-attestation cannot switch this on.
- Runtime resolver is privileged in-process composition, not an isolation mechanism against arbitrary malicious Python code or broad host credentials. It must never become an MCP argument. T12 still owns atomic execution, correct repo/ref binding, race handling and idempotency; T4 owns actual resource ownership.
- Read-only GitHub app installation identity, comprehensive branch-protection evaluation and external containment providers are not implemented. Unknown data fails closed. No claim of live GitHub enforcement verification is made.
- Windows automated tests: PASS. Native host installation matrix, native macOS execution and real-human product trials: NOT_RUN/UNVERIFIED. Product gates remain required; no unrun trial is claimed. Per the owner clarification, these future workflow proofs do not block implementation progress.

Official primary docs consulted for endpoint/schema behavior:

- [GitHub REST rules](https://docs.github.com/en/rest/repos/rules?apiVersion=2026-03-10): branch-rule endpoint returns active rules; evaluate/disabled enforcement is excluded.
- [GitHub REST workflows](https://docs.github.com/en/rest/actions/workflows?apiVersion=2026-03-10): workflow list is metadata, not safety certification.
- [GitHub REST Git refs](https://docs.github.com/en/rest/git/refs?apiVersion=2026-03-10): matching refs can include prefix matches; implementation uses paginated branch listing and exact branch names instead.
- [GitHub REST repositories](https://docs.github.com/en/rest/repos/repos?apiVersion=2026-03-10#get-a-repository): repository identity observations.
