# Verification and compatibility

Recorded 2026-11-07 (Asia/Bangkok). These are plugin construction checks, not PoC/MVP/Beta/Final certification of the plugin or human sessions for a managed project.

| Evidence | Observed result |
| --- | --- |
| Windows 11 x64, Python 3.14.4, locked dependencies | Automated suite: 289 passed, 2 skipped, warnings treated as errors |
| Native Windows supervision | Internal library: Job assignment, literal Unicode/metacharacter arguments, descendants, timeout, launch failure, crash phases, pending scratch cleanup, foreign-process preservation and ownership tests passed. Public execution is disabled pending real authority isolation |
| CLI integration | init/start/change/continue/backlog persisted across invocations; status read-only; stale requests rejected |
| Native host route | Reviewed native_tools scope selects host tools without a custom runner; missing lifecycle capabilities/pause/stale run denied; active jobs cannot disappear from work updates, handoff or next-run checks; cancellation remains pending until cleanup evidence |
| Real temporary Git repos | missing-only bootstrap, feature → Stage → develop, retained Stage, merged-feature deletion and protected-target rejection passed |
| QA/state fixtures | >95 boundary, High/unknown defects, traceability, stale build/matrix, takeover baseline gate, feedback waiting and whole-Stage backlog behavior passed |
| Frozen Windows runtime | PyInstaller native onedir build passed; real stdio initialize/list_tools/status/init/start passed; forged approval rejected; optional execute returns ISOLATION_REQUIRED and native-plan without kickoff returns NOT_AUTHORIZED |
| Host package assembly | Codex/Claude/Devin manifests, skills, relative MCP runtime paths and contained ZIP payloads exercised by tests |
| Skill pressure simulation | Baseline refused ordinary native tests due to optional executor refusal; revised instructions allow approved bounded native tests, preserve protected staging merge refusal and distinguish owner-authorized plugin-build push. Earlier scope/team/Stage pressure checks also pass. Agent simulation only |
| Native macOS | NOT_RUN on this Windows machine; source and Mac-native build procedure supplied |
| Installed Claude Code / Devin | NOT_RUN: those hosts are not installed here; no license/account or native desktop check fabricated |
| Codex | CLI 0.162.0-alpha.17.2 help inspected; no plugin installed into the user's settings without a separate installation request |
| Real human trials | NOT_APPLICABLE to building the plugin; managed-project requirements are implemented and fixture-tested, not claimed to have recruited real people |
| Remote Git writes | DISABLED / LOCAL_ONLY until effective containment is provable; prepare owner-reviewable PR drafts instead |

The Windows skip reasons are unavailable symlink privilege and the native macOS-only probe. Temporary directory junction checks still run on Windows. Test fixtures inject a review callback strictly inside tests; production MCP exposes no user approval endpoint.

The runtime cannot authenticate people from JSON flags or prove tool execution from arbitrary submitted logs. It binds evidence to a frozen scope, matrix and source fingerprint, requires independent team review and a separate user channel for human gates, and reports limitations. An unrestricted host can run unrelated tools outside the runtime; this plugin is not an OS sandbox for those tools.

Reproduce: `uv sync --locked --group dev`, then `python -m pytest -q -W error` inside the plugin environment. Build with `python scripts/build_runtime.py`. Exercise the resulting process with `python scripts/smoke_mcp.py ABSOLUTE_RUNTIME_EXECUTABLE`. Native Mac checks and host activation remain explicitly unverified until performed on those actual targets.

The optional standalone recipe API remains unavailable, even with legacy execute_recipes permission, closing a demonstrated own-runtime protected-ref bypass. Scoped development/tests/servers/browsers instead use each host's native tools with native_tools permission, observed timeout/owned-cleanup capabilities and lifecycle evidence; no custom runner is a product prerequisite. Effective executable Git extensions still cause local Git automation to refuse the repository. This is agent orchestration, not an OS security boundary around unrelated host tools. See docs/development/review-and-decisions.md in the source repository.
