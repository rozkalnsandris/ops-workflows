# ops-workflows

Reusable GitHub Actions and cross-project delivery policy for the `rozkalnsandris` repositories.

## Scope

This repository contains shared GitHub-side automation and policy:

- reusable `workflow_call` workflows;
- FAST-LANE v2.2 Composite delivery policy;
- the FAST-LANE v2.2 decision record and migration rationale;
- Auto-Live v1 shared post-merge delivery contract;
- SIMPLE-DEPLOY v1 shared platform design for one reusable deployment model across compatible services;
- AUTO-RUN FULL Queue v1 shared source-policy design;
- legacy `GITHUB-ONLY` / `LIVE-ALL` deferred deployment policy and queue during consumer migration;
- public-repository CI/security policy;
- action full-SHA pinning checks;
- public-runner safety checks;
- deterministic GitHub-side audit policy.

It must not contain RPi5 production credentials, host mutation logic, systemd units, production deploy helpers, database apply logic, private keys, or arbitrary remote-execution bridges.

The canonical automation master plan and host-control logic remain in `rozkalnsandris/RPi5_main`.

## Delivery platform sequence

Canonical cross-project sequencing is documented in:

`docs/DELIVERY_PLATFORM_ROADMAP.md`

The current platform order is deliberately serial:

```text
1. ops-workflows#97 — implement shared SIMPLE-DEPLOY workflow/policy/schema/tests
2. RPi5_main#666 — implement one generic trusted GHCR pull deployer
3. rozkalns_weather#142 — first consumer/canary adoption
4. one explicit Weather/RPi5 cutover LIVE gate
5. prove Weather end to end
6. migrate/test other compatible Docker/Compose services
7. declare SIMPLE-DEPLOY stable/default
8. ONLY THEN ops-workflows#96 — AUTO-RUN FULL Queue vNext
```

Do not implement Queue vNext in parallel with SIMPLE-DEPLOY rollout. Current Queue v1/A1 remains source-policy design until later explicit adoption.

## FAST-LANE v2.2 Composite

Core operating rule:

> **The human approves the RISK / DECISION. Automation executes the TECHNICAL STEPS.**

The normal workflow has at most two owner decisions:

1. exact **MERGE** authorization;
2. one bounded **COMPOSITE LIVE** authorization only when live mutation is actually required.

Read-only technical checkpoints are automated and do not create owner gates. Merge never authorizes live mutation.

Canonical normative policy:

`docs/FAST_LANE_V2_1_HYBRID.md`

The filename above is intentionally retained as a compatibility path for repositories that adopted v2.1 before the v2.2 upgrade. Its contents are the active v2.2 policy.

Detailed decision record, migration rationale, historical evidence, anti-patterns, state machine, Composite Live examples, and 2026-08-22 rollout receipt:

`docs/FAST_LANE_V2_2_DECISION_RECORD.md`

Machine-readable invariants:

`policy/fast-lane-v2.2.json`

All owner repositories may adopt the same external vocabulary (`FAST`, `STRICT`, Ready receipt, exact merge gate, Composite Live envelope, bounded corrections) while keeping project-specific stricter safety rules and CI classification locally.

## Auto-Live v1

Auto-Live v1 is the shared normal-operation target for production-bearing consumers after each repository/target has explicitly migrated and activated its reviewed manifest and trusted controller path. Merge is a reconciliation trigger, not blanket live authority.

Canonical shared contract:

`docs/AUTO_LIVE_V1.md`

Machine-readable invariants:

`policy/auto-live-v1.json`

`ops-workflows` remains GitHub-side only; trusted production execution stays in the consuming runtime project. No manifest means no automatic live mutation. Consumers must pin accepted production policy references to an immutable exact commit SHA.

## SIMPLE-DEPLOY v1 — design / not active

Architecture umbrella `#94` defines the planned shared deployment platform for compatible current and future services.

Canonical design plan:

`docs/SIMPLE_DEPLOY_V1_PLAN.md`

Canonical implementation/sequence clarifications:

`docs/DELIVERY_PLATFORM_ROADMAP.md`

Current shared implementation work item:

`#97`

Generic trusted runtime executor source:

`rozkalnsandris/RPi5_main#666`

First consumer/canary:

`rozkalnsandris/rozkalns_weather#142`

Target ordinary-release UX after a consumer has explicitly migrated and completed its one-time cutover:

```text
AUTO-RUN FULL
-> exact-head CI PASS
-> guarded merge
-> tiny consumer caller
-> shared reusable SIMPLE-DEPLOY workflow
-> GitHub-hosted image build
-> GHCR exact-SHA image + immutable digest
-> stable production desired-digest pointer
-> generic trusted RPi5 pull deploy
-> docker compose up --wait
-> health/readiness
-> deployed digest receipt
-> LIVE
```

Key implementation rules:

- `ops-workflows` owns reusable GitHub-side policy/workflows, image publication/promotion, schemas, shared tests and migration rules;
- `RPi5_main` owns one generic trusted allowlisted pull deployer rather than per-project deploy engines;
- consumer repositories keep only a tiny immutable-SHA-pinned caller plus application-specific manifest and health/persistence identities;
- the mutable production tag/channel is discovery only; the exact resolved GHCR digest is the deployment identity frozen for an attempt;
- public images containing no private runtime configuration should support anonymous public GHCR pull; private registry auth is a separate reviewed profile;
- reusable workflow callers grant only least privileges, normally `contents: read` plus `packages: write` where image publication requires it;
- `environment: production` is used for deployment history/policy, but a manual required reviewer is not part of the baseline one-approval `AUTO_DEPLOY_SAFE` UX;
- production concurrency is centrally owned by the shared architecture; callers must not create a competing generic concurrency controller;
- production consumers pin the accepted shared workflow/policy to a full immutable `ops-workflows` SHA and include the documented Renovate-compatible version comment/tag convention; never consume mutable `@main`.

The design reuses Auto-Live exact-target/reconciliation/concurrency/fail-closed primitives and keeps Simple LIVE for sensitive or exceptional operations. It does not permit `ops-workflows` to become a credential store, generic remote shell, privileged RPi5 runner or arbitrary production transaction engine.

This is **not active production policy yet**. Existing consumer repository-local deployment contracts remain authoritative until each consumer explicitly adopts the final shared contract and completes its reviewed cutover.

## AUTO-RUN FULL Queue v1

AUTO-RUN FULL Queue v1 is the shared **current source-policy design** for higher-throughput sequential implementation: up to ten explicitly named ordered issues, with only one issue active at a time.

Canonical current A1 design:

`docs/AUTO_RUN_FULL_QUEUE_V1.md`

Machine-readable A1 invariants:

`policy/auto-run-full-queue-v1.json`

A1 is intentionally **not active in consumers**. Existing repository-local AUTO-RUN FULL contracts remain authoritative until a consumer explicitly adopts a later completed Queue contract pinned to an immutable `ops-workflows` commit SHA. A shared-policy merge never auto-migrates a repository and never grants queue-wide merge or LIVE authority.

### Planned Queue vNext after SIMPLE-DEPLOY fleet rollout

Tracking issue `#96` records the future target requested after SIMPLE-DEPLOY is implemented, canary-tested and adopted across intended compatible services.

Future target UX:

```text
AUTO-RUN FULL QUEUE repo #1 #2 #3 #4

#1 -> source -> CI -> merge -> SIMPLE-DEPLOY -> receipt -> #2
#2 -> source -> CI -> merge -> SIMPLE-DEPLOY -> receipt -> #3
...
```

One explicit ordered queue activation will eventually allow normal successful items to advance without another owner approval between them. The owner is interrupted only for genuine problems/risk/gates.

This **does not change current Queue v1 authority today**. The current A1/Simple LIVE text remains the current inactive design until #96 is explicitly implemented after fleet stability.

## GITHUB-ONLY / LIVE-ALL

Canonical deferred-deployment operator policy:

`docs/GITHUB_ONLY_LIVE_ALL.md`

Machine-readable contract:

`policy/github-only-live-all-v1.json`

Canonical queue transport:

GitHub Issues in this repository using `.github/ISSUE_TEMPLATE/deploy-queue.yml` and the title prefix `[DEPLOY-QUEUE]`.

- `GITHUB-ONLY` performs GitHub/source-level work and prepares every required ordinary deploy up to the first live mutation.
- Deferred rollout state is persisted in GitHub, never only in chat/memory.
- `LIVE-ALL` snapshots the currently open `READY` queue issues, freshly revalidates each exact SHA/target/baseline, and executes only the predeclared ordinary rollout envelopes sequentially by default.
- Merge, DB writes/migrations, secrets/credentials, permission/trust-boundary expansion, destructive cleanup, DNS/Tunnel/Access changes and undeclared high-risk work remain separately gated.
- After a live mutation starts, an error or ambiguous result stops the remaining batch without automatic retry/rollback/cleanup unless explicitly pre-authorized.

Because this repository is public, queue issues must contain only public-safe operational metadata. Private credentials or protected runtime configuration never belong here.

## Public repository baseline

Reusable workflow:

`.github/workflows/public-repo-baseline.yml`

It enforces:

- GitHub-hosted runner policy for public repositories;
- external Actions and reusable workflows pinned to full 40-character commit SHAs;
- no `permissions: write-all`;
- least-privilege caller permissions;
- project-specific CI remains in each consuming repository.

Consumers must reference this repository by an exact 40-character commit SHA after the canary is proven. Do not consume `main`, a mutable tag, or a version branch for production policy.

Private repositories may adopt FAST-LANE process policy without consuming the public-repository baseline workflow when that workflow is not applicable.

## Safety boundary

`ops-workflows` is not a production execution environment. Trusted production execution stays local to the owning runtime project behind exact-SHA/digest gates and narrow reviewed helpers.
