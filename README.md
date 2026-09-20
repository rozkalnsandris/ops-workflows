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

Tracking issue `#94` defines the planned shared deployment platform for compatible current and future services.

Canonical design plan:

`docs/SIMPLE_DEPLOY_V1_PLAN.md`

Target ordinary-release UX after a consumer has explicitly migrated and completed its one-time cutover:

```text
AUTO-RUN FULL
-> exact-head CI PASS
-> merge
-> shared reusable SIMPLE-DEPLOY workflow
-> GitHub-hosted image build
-> GHCR exact-SHA image + immutable digest
-> production promotion
-> trusted RPi5 pull deploy
-> docker compose up --wait
-> health/readiness
-> LIVE
```

The intended architecture is deliberately split:

- `ops-workflows` owns reusable GitHub-side policy/workflows, image publication/promotion, schemas, shared tests and migration rules;
- `RPi5_main` owns one generic trusted `rozkalns-simple-deployer`-style host executor;
- consumer repositories keep only a tiny immutable-SHA-pinned caller plus application-specific deployment manifest and health/persistence identities.

Production consumers will pin the accepted shared workflow/policy to an immutable full `ops-workflows` commit SHA. Central changes will be validated/canaried first, then propagated through Renovate-managed pin-update PRs instead of mutable `@main`, avoiding an immediate fleet-wide blast radius while retaining one centrally maintained implementation.

The design reuses Auto-Live exact-target/reconciliation/concurrency/fail-closed primitives and keeps Simple LIVE for sensitive or exceptional operations. It does not permit `ops-workflows` to become a credential store, generic remote shell, privileged RPi5 runner or arbitrary production transaction engine.

Planned migration sequence:

1. shared SIMPLE-DEPLOY source/policy/workflow in `ops-workflows`;
2. one generic trusted deployer in `RPi5_main`;
3. `rozkalns_weather#142` as first canary;
4. migrate Hermes Deals and other compatible Docker/Compose services;
5. make SIMPLE-DEPLOY the default bootstrap for future compatible projects after at least two consumers prove reuse.

This is **not active production policy yet**. Existing consumer repository-local deployment contracts remain authoritative until each consumer explicitly adopts the final shared contract and completes its reviewed cutover.

## AUTO-RUN FULL Queue v1

AUTO-RUN FULL Queue v1 is the shared **source-policy design** for higher-throughput sequential implementation: up to ten explicitly named issues may be frozen into one ordered queue, but only one issue is active at a time.

Target lifecycle:

```text
frozen issues
-> one ACTIVE issue
-> source / PR / CI / review / merge / exact-main verification
-> next issue
-> final exact-main + read-only preflight
-> one final owner LIVE decision only if live mutation is required
-> fixed reviewed consumer rollout
```

Canonical design:

`docs/AUTO_RUN_FULL_QUEUE_V1.md`

Machine-readable A1 invariants:

`policy/auto-run-full-queue-v1.json`

A1 is intentionally **not active in consumers**. Existing repository-local AUTO-RUN FULL contracts remain authoritative until a consumer explicitly adopts a later completed Queue contract pinned to an immutable `ops-workflows` commit SHA. A shared-policy merge never auto-migrates a repository and never grants queue-wide merge or LIVE authority.

The Simple LIVE direction is intentionally narrow: exact SHA + exact target + one fixed reviewed consumer operation, with read-only preflight first, per-target serialization, fail-closed post-mutation behavior and one final receipt. `ops-workflows` remains policy/guard infrastructure rather than a generic production executor.

Tracking issue: `#39`.

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

`ops-workflows` is not a production execution environment. Trusted production execution stays local to the owning runtime project behind exact-SHA CI gates and narrow, separately authorized helpers.
