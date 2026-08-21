# ops-workflows

Reusable GitHub Actions and cross-project delivery policy for the `rozkalnsandris` repositories.

## Scope

This repository contains shared GitHub-side automation and policy:

- reusable `workflow_call` workflows;
- FAST-LANE v2.1 Hybrid delivery policy;
- public-repository CI/security policy;
- action full-SHA pinning checks;
- public-runner safety checks;
- deterministic GitHub-side audit policy.

It must not contain RPi5 production credentials, host mutation logic, systemd units, production deploy helpers, database apply logic, private keys, or arbitrary remote-execution bridges.

The canonical automation master plan and host-control logic remain in `rozkalnsandris/RPi5_main`.

## FAST-LANE v2.1 Hybrid

Canonical policy:

`docs/FAST_LANE_V2_1_HYBRID.md`

Machine-readable defaults:

`policy/fast-lane-v2.1.json`

All owner repositories may adopt the same external workflow vocabulary (`FAST`, `STRICT`, Ready receipt, bounded corrections, explicit merge gate) while keeping project-specific stricter safety rules and CI classification locally.

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
