# Native implementation review and decisions

Date: 2026-11-07 Asia/Bangkok. Managed-project maturity stages were never construction gates for this implementation.

One fresh whole-branch review examined 2133632..92e4f70. Initial verdict: six Important findings, no Critical or Minor. A single implementation fix pass added failing regressions, corrected behavior and ran the full suite: **272 passed, 2 skipped, warnings as errors**. The reviewer was not asked to re-review the same changes. A separate author-discovered loss of old Stage guides was also reproduced and fixed.

| Finding | Final disposition and evidence |
| --- | --- |
| Public recipes could mutate protected Git refs | Closed by removing public execution capability. A real temporary-repo regression reproduced deletion of main through a reviewed Git recipe, then passed with ISOLATION_REQUIRED and unchanged main. A Job/group manages lifetime, not authority isolation. No user flag enables execution |
| Configured Git filters/merge drivers executed external programs | Effective config and raw attributes across local heads/worktree/global/info files are checked before local automation; active executable extensions are refused, commands are neutralized per invocation, and repository config is preserved. Four regressions cover clean/smudge/process/merge drivers |
| Released capacity hid pending scratch cleanup | Pending queries include unresolved receipts and orphan cleanup obligations. Cleanup retries project-owned scratch while keeping stopped-workload capacity available. Regression verifies pending is visible and then removed |
| Pre-handle crash stranded reservations | Admission atomically stores launcher identity and phase, startup persists ownership before native launch, reconciliation enumerates missing handles. Native Windows probes crash after reservation and before handle persistence; both recover without TTL-based release. Unknown legacy/platform proof remains pending |
| Broken package README links and omitted examples | Package-specific README, static editable templates and marketplace example included. Tests resolve advertised package-local README links and template paths |
| macOS controlled tests were rejected and missing-executable semantics differed | Controlled cooperative fixture explicitly allowlisted; missing programs rejected before native launch on all drivers. Static/simulated boundary check passes; native Mac remains NOT_RUN |
| Old scope guides disappeared on next start | Completed/cancelled run artifacts, brief and receipts are archived. Guide retrieval by run ID is tested |

There are no deferred Minor findings from this review. This is a safe, explicitly limited local release; it does **not** demonstrate full autonomous test/server/browser execution or installed-host/macOS certification.

## Decisions made during implementation

1. Reuse the existing pinned isolated Python toolchain for building the plugin; it does not set managed-project Python versions. If wrong: adjust only the plugin toolchain.
2. Build through ordinary work packages A–F, preserving PoC/MVP/Beta/Final as managed-project data. This follows the owner's explicit correction. If wrong: revise the build plan, not client runtime state.
3. Use a small transactional document store for workflow artifacts; retain the earlier typed state library. If wrong: consolidate storage later.
4. Trust user reviews only through an injected composition-root channel; generic MCP elicitation does not prove a human. Use interactive CLI fallback. If wrong: additional integration friction or a trusted host adapter is needed.
5. Matrix/quality/guide reviews are team attestations; kickoff/baseline/real feedback/handoff/recovery use the user channel. If wrong: revise the approval map before granting additional automation.
6. Keep remote mutations disabled/LOCAL_ONLY while effective credential/workflow containment cannot be proved; produce owner-reviewable drafts. If wrong: remote publication stays manual until a verified adapter exists.
7. Freeze only the first proposed bounded Stage in a kickoff; reassess later scopes after handoff. If wrong: an additional scoped kickoff costs user time.
8. Generate thin host skills around shared coordinator instructions instead of duplicating the workflow across adapters. If wrong: add host-specific adapter extensions.
9. Refuse public arbitrary-process recipes until a real isolation driver enforces Git, credentials, filesystem and network limits. Keep the tested supervisor as an internal library. If wrong: automatic test/server/browser execution remains unavailable longer than needed.

## Certification boundaries considered by review

- macOS execution/signing/quarantine/architecture: do not certify on Windows. Supply native build steps and report NOT_RUN. Cost: native defects may remain until actual Mac verification.
- Installed Codex/Claude/Devin loaders: package/schema/process checks do not equal host activation. Do not silently install into the user's settings. Cost: loader/version differences may require an adapter adjustment.
- Human identity, test truth and unrelated host tools: JSON consistency and terminal detection are not authentication or an OS sandbox. Record owner/team attestations and disclose the boundary. Cost: trusted participants can supply inaccurate evidence; unrestricted outside-host actions are outside runtime enforcement.

Reproduction: final suite uses project-owned temporary roots; native helper processes and disposable Git repos only. No remote push/PR, external participant invitations, host installation or global Python/PATH/profile changes were performed.
