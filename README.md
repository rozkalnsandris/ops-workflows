# ops-workflows

Reusable GitHub Actions and cross-project delivery policy for the `rozkalnsandris` repositories.

## Scope

This repository contains shared GitHub-side automation and policy:

- reusable `workflow_call` workflows;
- FAST-LANE v2.2 Composite delivery policy;
- the FAST-LANE v2.2 decision record and migration rationale;
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
