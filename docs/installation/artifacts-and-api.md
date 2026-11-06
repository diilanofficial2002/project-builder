# Artifacts and command API

The host agent edits/builds/tests the client's application using its native tools. The Python runtime provides durable state, deterministic gates, local Git and cleanup evidence. It is not an independent code-generating LLM service or a required custom process runner.

MCP exposes one `project_builder` tool. Arguments: absolute `project_root`, `intent`, `payload` object, optional `request_id`, `expected_revision`, `run_id`. Mutations after init require a request ID and current revision; workers also send run ID. CLI gets a fresh revision unless explicitly supplied. Every CLI JSON response has status/summary/next_action/data; MCP returns data directly. `status`, `doctor`, `help`, `guide`, `backlog`, `discovery`, `artifacts`, `review-packet`, `operations` read without initializing state.

| Intent | Payload |
| --- | --- |
| init | kind: new / takeover / new-version |
| start | description |
| continue / pause / cancel / cleanup | empty object |
| change | text, urgent boolean (default false) |
| submit | kind and data document |
| feedback | data document (same as submitting feedback) |
| review-packet | subject: kickoff / matrix / quality / guide / baseline / feedback / handoff / recovery |
| qa-review | subject: matrix / quality / guide, digest, notes with actual independent findings/provenance |
| git | operation: bootstrap / stage / feature / integrate / delete-feature, plus name/stage/source/target as appropriate |
| native-plan | Read-only host-native guidance from observed tool capabilities; requires reviewed native_tools scope |
| execute | Optional standalone helper: always ISOLATION_REQUIRED; ordinary authorized host-native tools remain usable |

Submit via `project-builder submit brief path/to/brief.json --project PATH --json`. CLI files are limited to 1MiB. Artifacts belong in `.project-builder` or another excluded evidence directory so writing their reports does not change the application source fingerprint. Never edit the SQLite database or manufacture review receipts. Keep project metadata out of Git commits; init does not silently change an existing .gitignore.

## Brief

Standalone packages include editable JSON in `templates/`; copy these into project-owned metadata and edit them. Source developers can also use `scripts/create_example.py OUTPUT_DIRECTORY`. TODO answers deliberately leave discovery incomplete; replace them with reviewed facts, explicit N/A reasons and assumptions. The 14 answer keys are:

business_goal, users, scope, acceptance, business_rules, ux, data, architecture, runtime, quality, authority, resource_budget, human_feedback, delivery.

```json
{
  "answers": {"business_goal": "A concrete measurable outcome; complete all other discovery fields too"},
  "requirements": [{"id": "R1", "summary": "A usable greeting CLI", "acceptance": ["--name Ada prints Hello, Ada!"]}],
  "target": "final",
  "stage_options": {"feasibility_unknown": false, "first_slice_needed": false, "pilot_needed": false},
  "domains": ["cli"], "complexity": "mini", "risks": [],
  "permissions": ["local_git", "native_tools"], "recipes": []
}
```

complexity: mini/small/medium/large. Domains may include frontend/ui/backend/data/ai. Risks select applicable specialists (security/privacy/deployment/operations). The selected team defaults to one active specialist. The plan's stage list is a proposal; only its first bounded Stage is frozen by this kickoff, and the next scope is reassessed after handoff.

`native_tools` authorizes scoped host-native editing/build/test/browser work, subject to the host's own permissions, the immutable Git ceiling and agreed resource budget. `native-plan` takes `{ "capabilities": { "host":"codex", "run_tool":"ACTUAL_TOOL", "stop_tool":"ACTUAL_STOP_TOOL", "bounded_timeout":true, "owned_cleanup":true, "observed_from":"Real host tool schemas and inspected timeout/cleanup facilities" } }`. Host is codex/claude/devin. These caller-supplied capabilities are advisory, not authenticated proof. The CLI equivalent is `native-plan CAPABILITIES_JSON_FILE`. A polling/yield interval alone is not a workload deadline.

Optional recipe: `{ "id":"tests", "executable":"/absolute/path/to/project/.venv/bin/python", "argv":["-m","pytest","-q"], "env":{}, "memory_mb":128, "disk_mb":32, "timeout_seconds":120.0, "cooperative":true }`. Use the Windows .exe path there on Windows. This optional standalone plan does not enable public execute, which remains disabled because lifetime supervision does not isolate Git, credentials, filesystem or network. No approval enables that helper. Ordinary approved native host commands do not require it. Do not store secret values in recipe env.

## Native workload evidence

Submit a `work` artifact containing `native_jobs`, preserving every existing job identity. Each job has unique id, host, current run_id and status ACTIVE/CLEANUP_PENDING/CLEANED. Also retain actual native session/owned process identity, command, deadline and resource estimate. CLEANED needs a nonempty `cleanup_evidence` reference to observed exit and owned child/server/browser/scratch checks. Declare no native jobs explicitly with `{"native_jobs":[],"no_native_jobs_reason":"Actual reason"}` only when none ran. JSON is a team attestation, not OS proof. Register launches and reconcile interrupted launches using real tool evidence.

`status` includes `native_resources`. Handoff and new-run creation are blocked while declared host work is pending/unverified. Runtime cleanup cannot kill host-native sessions from submitted IDs; it returns CLEANUP_PENDING until the host performs owned cleanup and evidence is recorded. A cancelled run permits work lifecycle updates only, retaining other work fields and prior identities; completed evidence stays immutable. Never delete a job record to clear a cleanup gate.

## Matrix and results

Matrix: positive revision, requirements containing exactly all frozen requirement IDs, families containing every test family with boolean applicable and reason, and cases with unique id, family, requirement_ids, applicable and optional critical. N/A cases need na_reason. Each applicable family and requirement needs a case. Family names:

functional, regression, unit, integration-sit, uat, end-to-end, ux-ui, accessibility, compatibility, load-performance, security, privacy, data-quality, ai-evaluation, resilience-recovery, installation-cleanup.

Results: matrix_digest (SHA256 of canonical JSON), build_sha (from artifacts), results array of `{case_id,status,attempts}` and optional producer/command/log evidence. Statuses: passed, failed, skipped, blocked, not-run, xfail. A missing case remains in the denominator. Do not set accept_retry_pass unless the independently reviewed matrix explicitly permits that retry policy. Labels do not multiply cases. High/critical open defects block; unknown severity is unverified. Every critical case must pass; pass ratio strictly greater than 95%.

Defects artifact is an array; each finding has id, severity low/medium/high/critical, status, description and evidence references. Resolved/closed findings require fix_evidence and retest_evidence; false-positive findings require review_evidence. Empty array means the producing QA actually found no defects, not that scans were skipped.

The runtime validates consistency and declared evidence; it cannot prove an agent executed a tool from JSON alone. The coordinator must retain real commands/logs and use an independent QA pass. Test fixtures in this repository are simulations, never human-trial or native-platform certification.

## Guide and real feedback

Guide: build_sha, nonempty setup_steps, run_steps, stop_steps, cleanup_steps; add prerequisites, configuration, expected output and limitations. Bind to current source. A guide review invalidates when the build changes.

Baseline/feedback: build_sha, participants array of exactly 2–3 unique anonymous IDs with real_user:true, independent:true, unfamiliar:true and source reference; observations array with severity/status/description/evidence. These flags are proposals until the owner reviews the actual evidence through the user channel. People unfamiliar with the product are independent of one another; fresh AI agents cannot substitute. Do not put personal data into a public repository. Baseline is required once at first takeover receipt, and feedback after each actual managed Stage. Current feedback and guide must match the tested build.

## State and failure behavior

Discovery → kickoff review → scoped work → verification → Stage feedback → handoff → completed. Takeovers begin with baseline feedback. Paused/cancelled work preserves checkpoint and code. Requirement revisions after scope freeze queue as backlog; normal changes wait until the whole Stage ends. Every scope is reassessed, including direct-to-Final choices.

The state directory is project-owned. Source fingerprints exclude metadata, environments, build output and dependency directories. Git HEAD plus staged/unstaged/untracked application content binds quality; excessive dirty content or unverifiable symlink/deletion stops fingerprinting and asks you to commit/narrow scope. The internal supervisor library (not exposed as an executable recipe tool) uses a machine-wide lease ledger; stale leases need proof-based cleanup rather than expiry. UNKNOWN external operations require recovery review and never become an automatic success.
