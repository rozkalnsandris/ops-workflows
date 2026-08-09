# ops-workflows

Reusable GitHub Actions and public-repository automation policy for the `rozkalnsandris` repositories.

## Scope

This repository contains only shared GitHub-side automation:

- reusable `workflow_call` workflows;
- public-repository CI/security policy;
- action full-SHA pinning checks;
- public-runner safety checks;
- deterministic GitHub-side audit policy.

It must not contain RPi5 production credentials, host mutation logic, systemd units, production deploy helpers, database apply logic, or private keys.

The canonical automation master plan and host-control logic remain in `rozkalnsandris/RPi5_main`.

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

## Safety boundary

`ops-workflows` is not a production execution environment. Trusted production execution stays local to RPi5 behind exact-SHA CI gates and narrow root-owned helpers documented in `RPi5_main`.

`rozkalnsandris/hermes-email-skill` is outside the automation program and is not managed by this repository.
