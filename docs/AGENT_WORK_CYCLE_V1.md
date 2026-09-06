# Agent Work Cycle v1

Status: ACTIVE shared governance baseline
Owner: Andris Rožkalns
Canonical repository: `rozkalnsandris/ops-workflows`
Reference implementation: `rozkalnsandris/RPi5_main`
Umbrella rollout tracker: `ops-workflows#31`

## Purpose

Provide one predictable operator interaction model across active repositories while preserving each repository's own product, deployment and trust-boundary rules. The contract standardizes how an agent bootstraps, refreshes, continues, stops and tells the owner exactly what to do next. It does not standardize or broaden production authority.

## Work-cycle model

`START <repo>` performs minimum-sufficient bootstrap using repository-local routing. Read current local rules, current default-branch SHA, canonical handoff/continuation when present, then identify one current work item/lane/gate. Inspect only the issue/PR/dependency evidence required for that lane.

`SYNC <repo>` is incremental refresh. Re-check current default branch, current work item, current PR/head and current checks/reviews against the active assumptions. Do not turn SYNC into a repo-wide inventory.

`turpini` resumes the exact same scope. It permits only the technical continuation already allowed by local policy and creates no new owner authority.

Repository-wide or multi-lane audits remain explicit audit work, not an implicit side effect of START/SYNC.

## Owner gates

Safe source work should converge through implementation, tests, Draft PR, CI/review and Ready without artificial owner interruptions when local rules permit. Polling CI, inspecting exact-head state, read-only preflight and scope-preserving corrections are technical steps rather than owner decisions.

MERGE remains explicit unless a repository's separately activated FULL mode explicitly freezes issue-scoped merge authority. Merge never grants LIVE/deploy authority.

LIVE/deploy/runtime/credentials/permissions/production-data changes remain separate exact owner gates according to repository-local policy. Authorization consumption and fail-closed rules remain local and may be stricter than this baseline.

## Fail-closed continuation

After the first authorized mutation begins, any error, timeout, unexpected state, target/head drift or authorization uncertainty ends mutation authority for that run unless retry/rollback/cleanup was explicitly pre-authorized. Gather only the necessary read-only evidence and STOP. Never turn a presentation command into implicit authority.

## Exact Next Command Contract

Every user-visible terminal/status response for repository work ends with exactly one copy-pasteable command, as its final actionable content.

1. Genuine owner gate exists -> `ACTION REQUIRED` with the exact current authorization command and bindings.
2. No owner gate; mutable GitHub/external state needs refresh -> `SYNC <repo>`.
3. No owner gate; same-scope technical continuation is safe now -> `turpini`.
4. Current outcome is complete -> `START <repo>`.

`ACTION REQUIRED` is reserved for genuine owner decisions. Do not invent MERGE/LIVE/retry/rollback/cleanup authority simply to produce a command. Never output a menu of next commands.

## Rollout scope

Active rollout repositories: `ops-workflows`, `hermes-deals`, `hermes-tech`, `rozkalns-cv`, `rozkalns-control-center`, `dashboard_RPi5`, `RPi5-maintenance`, `home-assistant-config`, `balcony-irrigation-esp32`. `RPi5_main` is the reference implementation.

Excluded from this rollout: `deploy-authorizations` (authorization ledger), `hermes-email-skill` (explicit automation-program exclusion), and `YouTube_Marcim` (unrelated private project). Repository-local stricter contracts always win.
