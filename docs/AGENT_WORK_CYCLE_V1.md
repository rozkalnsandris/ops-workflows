# Agent Work Cycle v1

Status: ACTIVE shared governance baseline
Owner: Andris Rožkalns
Canonical repository: `rozkalnsandris/ops-workflows`
Reference implementation: `rozkalnsandris/RPi5_main`
Umbrella rollout tracker: `ops-workflows#31`

## Purpose

Provide one predictable operator interaction model across active repositories while preserving each repository's own product, deployment and trust-boundary rules. The contract standardizes how an agent bootstraps, refreshes, continues, stops and tells the owner exactly what to do next. It does not standardize or broaden production authority.

## Work-cycle model

`START <repo>` performs minimum-sufficient bootstrap using repository-local routing. Read current local rules, current default-branch SHA, canonical handoff/continuation when present, then identify exactly one current work item/lane/gate. Inspect only the issue/PR/dependency evidence required for that lane.

After one canonical lane is selected, `START <repo>` continues all immediately safe same-scope technical work until a genuine terminal condition exists. It must not normally return a status equivalent to “the next safe technical step is X” when X can be executed immediately under current authority.

`SYNC <repo>` is incremental refresh of the already-selected/current lane. Re-check current default branch when relevant, current work item, current PR/head and current checks/reviews against the active assumptions. Do not turn SYNC into a repo-wide inventory or restart lane selection without evidence that continuation changed.

`turpini` resumes the exact same scope using minimum-sufficient incremental reads and continues safe technical work. It creates no new merge, LIVE, retry, rollback, cleanup, credential, permission, repository-settings, runtime or production-data authority.

`AUDIT-HANDOFF <repo>` and other repository-wide or multi-lane audits remain explicit deeper audit work. They are never an implicit side effect of normal START/SYNC/turpini.

## Safe auto-continuation

The normal work-cycle target is:

```text
resolve repository-local rules / BOOTSTRAP_MANIFEST_V1 when adopted
-> BOOTSTRAP_MINIMAL
-> select exactly one canonical lane
-> execute immediately safe same-scope technical work
-> stop only at:
   1. genuine owner authorization/decision gate
   2. external wait with no remaining safe advance
   3. fail-closed error, drift or ambiguity
   4. DONE
```

Safe technical continuation does not itself create an owner gate. Subject to repository-local authority and scope, it includes:

- minimum-sufficient GitHub reads;
- source inspection;
- focused source/docs/policy edits inside the active scope;
- local/static tests;
- branch/PR preparation when the active repository-local mode already authorizes it;
- exact-head CI/review refresh;
- scope-preserving corrective work inside the active attempt budget;
- read-only preflight/evidence refresh;
- exact-main read-only reconciliation after a confirmed write.

If a current PR is waiting on CI/review and no other same-scope safe step can advance the lane, an external-wait terminal state is valid. If same-scope safe work still exists, perform it first.

A repository-local explicitly activated FULL mode may already freeze issue-scoped source or merge authority. The shared work cycle must not insert a second generic owner gate inside authority that the stricter local contract already validly grants. Conversely, a source lane that reaches a LIVE/deploy/runtime/DB/data/credential/permission/settings/trust-boundary requirement must stop before that mutation unless the exact local authority already exists.

## Bootstrap manifest routing

Optional routing contract: `docs/BOOTSTRAP_MANIFEST_V1.md`, with machine policy in `policy/agent-bootstrap-v1.json` and schema in `policy/schemas/agent-bootstrap-v1.schema.json`.

When a repository has adopted `.github/agent-bootstrap.json`, normal `START <repo>` may read that small manifest first to resolve the primary repository-local rules, shared work-cycle/API-access surfaces, stable continuation locator, supported automation modes, and deployment-routing profile. The manifest is routing metadata only; repository-local normative rules remain authoritative and stricter rules always win.

The manifest must never substitute cached mutable SHA, PR, CI/review, mergeability, runtime/deployed revision, authorization-consumed state, secrets, or credentials for fresh canonical reads. After routing is resolved, normal bootstrap still performs the current default-branch and selected-lane reads required by `GITHUB_API_ACCESS_V1` `BOOTSTRAP_MINIMAL`.

A missing manifest preserves the legacy repository-local startup path. If a manifest is malformed, stale, or references missing canonical surfaces, fall back to unambiguous repository-local rules; if routing is also ambiguous, fail closed and STOP rather than selecting a less strict interpretation.

## GitHub-first tool and transport priority

GitHub is the default control, read and write surface whenever repository/source work can be completed through connected GitHub tooling with equivalent correctness and evidence. Do not use RDC, SSH, a local checkout, shell `git`, `gh`, or `curl` merely as a substitute for supported GitHub-native operations.

Use RDC/host shell only for the smallest step that genuinely requires execution or observation on the RPi5/host and cannot be obtained through GitHub, such as host/runtime evidence, local filesystem/process state, `sudo`/root, systemd, Docker, packages, networking, mounts, permissions/ownership, or another command that must execute on that host.

When a task spans both surfaces, use **GitHub -> minimal required RDC/host step -> GitHub**. Return to GitHub for canonical source, branches/commits/PRs, issues, CI/reviews and durable continuity/evidence. RDC is execution/transport only and never source-of-truth or authorization authority.

Choosing RDC never widens owner-authorized mutation classes, targets, protected-data access, retry/rollback/cleanup authority, merge authority, repository-settings authority, or secrets/permissions authority. Repository-local stricter runtime and protected-data rules always win.

## GitHub API access and rate-limit discipline

Shared access contract: `docs/GITHUB_API_ACCESS_V1.md` with machine invariants in `policy/github-api-access-v1.json`.

Normal work-cycle retrieval is serial and minimum-sufficient by default. Prefer event/state-driven continuation over tight polling, use conditional requests only when the active transport exposes them, keep pagination and GraphQL bounded, and reuse already-returned evidence within the same decision step when sufficient.

For an active PR, normal `START`/`SYNC`/`turpini` reads stay on the selected lane: current main when relevant, exact PR head, required checks/status, reviews and unresolved threads. Changed-file enumeration is on-demand only, unrelated historical workflow runs/comments/commits are not fetched by default, and an aggregate connector operation is preferred when it already returns the same required canonical evidence. Explicit `AUDIT-HANDOFF` or a concrete failure/conflict may broaden retrieval, but normal convergence does not.

CI/review refresh is event/state/user-continuation driven rather than a tight loop. Do not repeatedly fetch an unchanged file list or unrelated historical workflow state while waiting for exact-head CI/review changes.

Before any mutation, rate-limit responses may trigger only the bounded read-only backoff allowed by the shared contract and repository-local stricter attempt limits. Rate-limit handling never creates merge/write authority. After an authorized mutation is dispatched/started, `403`, `429`, timeout, transport failure, or uncertain completion must not cause an automatic duplicate mutation; preserve/reconcile only the minimum permitted evidence and fail closed under repository-local rules.

## Owner gates

Safe source work should converge through implementation, tests, Draft PR, exact-head CI/review and Ready without artificial owner interruptions when local rules permit. Polling CI, inspecting exact-head state, read-only preflight and scope-preserving corrections are technical steps rather than owner decisions.

MERGE remains explicit unless a repository's separately activated FULL mode explicitly freezes issue-scoped merge authority. Merge never grants LIVE/deploy authority.

LIVE/deploy/runtime/credentials/permissions/production-data changes remain separate exact owner gates according to repository-local policy. Authorization consumption and fail-closed rules remain local and may be stricter than this baseline.

## Fail-closed continuation

After the first authorized mutation begins, any error, timeout, unexpected state, target/head drift or authorization uncertainty ends mutation authority for that run unless retry/rollback/cleanup was explicitly pre-authorized. Gather only the necessary read-only evidence and STOP. Never turn a presentation command into implicit authority.

## Compact terminal response contract

Normal repository work-cycle terminal/status responses are intentionally compact. Include only evidence that changes the current decision and omit empty optional fields.

Preferred shape:

```text
STATE: <one-line state>
EVIDENCE: <up to four decisive facts, when needed>
DONE: <what completed, when useful>
NOT DONE / BLOCKER: <only when applicable>

<exactly one final copy-pasteable next command>
```

Use `ACTION REQUIRED` only immediately before the final command when a genuine owner authorization/decision gate exists. Do not use it for CI waiting, read-only refresh, ordinary same-scope technical continuation, or DONE.

Do not replay long history during normal START/SYNC/turpini. If immediately executable same-scope safe work remains, perform it before returning a terminal response. `turpini` is a valid final command only when the current execution/session boundary genuinely pauses while same-scope safe technical continuation still remains.

## Exact Next Command Contract

Every user-visible terminal/status response for repository work ends with exactly one copy-pasteable command, as its final actionable content.

1. Genuine owner gate exists -> `ACTION REQUIRED` with the exact current authorization command and bindings.
2. No owner gate; mutable GitHub/external state must change before work can continue -> `SYNC <repo>`.
3. No owner gate; the current execution boundary pauses while same-scope safe technical continuation remains -> `turpini`.
4. Current outcome is complete -> `START <repo>`.

The command selection contract is presentation only. It never creates authority. Do not invent MERGE/LIVE/retry/rollback/cleanup authority simply to produce a command and never output a menu of next commands.

## Rollout scope

Active rollout repositories: `ops-workflows`, `RPi5_main`, `hermes-deals`, `hermes-tech`, `rozkalns-cv`, `rozkalns-control-center`, `dashboard_RPi5`, `RPi5-maintenance`, `home-assistant-config`, `balcony-irrigation-esp32`, `rozkalns_weather`, `linux-operations-lab`.

Excluded from this rollout: `deploy-authorizations` (authorization ledger), `hermes-email-skill` (explicit automation-program exclusion), `YouTube_Marcim` (unrelated private project), and the `rozkalnsandris` profile repository (profile-only metadata, not an engineering work repository). Repository-local stricter contracts always win.
