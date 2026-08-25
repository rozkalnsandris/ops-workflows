# ops-workflows

Reusable GitHub Actions and cross-project delivery policy for the `rozkalnsandris` repositories.

## Scope

This repository contains shared GitHub-side automation and policy:

- reusable `workflow_call` workflows;
- FAST-LANE v2.2 Composite delivery policy;
- the FAST-LANE v2.2 decision record and migration rationale;
- `GITHUB-ONLY` / `LIVE-ALL` deferred deployment policy and queue;
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
