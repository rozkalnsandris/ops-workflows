# GitHub-first / RDC fallback v1

Status: shared governance proposal (effective only after merge and explicit consumer adoption)
Canonical repository: `rozkalnsandris/ops-workflows`
Parent: `docs/AGENT_WORK_CYCLE_V1.md`
Machine contract: `policy/github-first-rdc-fallback-v1.json`

## Normative rule

**Perform each step in GitHub whenever a supported connected GitHub operation or GitHub-hosted CI can provide equivalent correctness, permission checks and durable evidence.** Selecting RDC because it is faster, familiar, or already connected is forbidden. Decide per step, not once for the entire task.

For source, files, branches, commits, issues, PRs, reviews, CI status, GitHub configuration reads and canonical continuity, GitHub is the default. Use GitHub-native actions for mutations and GitHub Actions for runnable source validation when available. Do not replace them with RDC shell `git`, `gh`, `curl`, SSH, or a host checkout.

RDC is an **exception**, not an interchangeable tool. It is eligible only when the exact necessary operation cannot be performed through supported GitHub tooling or safe GitHub-hosted CI with equivalent evidence, and the operation is actually appropriate on the authorized host. Typical examples: host-local services/processes, systemd, Docker runtime, filesystem and device state, networking, packages, mount/ownership checks, and expressly approved host-local tests. Use the smallest necessary read/command and return immediately to GitHub.

## Required decision sequence

1. Identify the exact task, repo, target, required read/write classification and existing owner authority.
2. Check the available connected GitHub operation for the step; use GitHub-hosted CI for source validation when applicable. Do not require shell access just to run tests when Actions can do so.
3. If GitHub can do it with equivalent correctness, **use GitHub**. No RDC choice is allowed.
4. If GitHub genuinely cannot do this step, record the concrete missing capability and why GitHub-hosted CI is not an equivalent path, verify that RDC can execute only the necessary host-local step and that applicable host/LIVE/permission authority already exists. If any proof or authority is missing: **STOP**.
5. Execute only the bounded authorized RDC step. Collect non-sensitive evidence, return to GitHub for any source/issue/PR/CI/continuity work, and preserve exact identities.
6. If a GitHub write was dispatched and its result is failed, rate-limited, timed out or uncertain, **STOP**. Do not switch to RDC for a duplicate write, retry, rollback, cleanup or alternate mutation path.

Before RDC, document a compact exception record: `step`, `repo/target`, `GitHub capability checked`, `precise blocker`, `why GitHub Actions cannot substitute`, `minimal RDC action`, `existing authorization`, and `return-to-GitHub evidence`. Do not put credentials, private paths, tokens or protected payloads in public receipts.

## Decision examples

| Step | Route |
| --- | --- |
| Fetch/update source, create a branch/commit, open a Draft PR, read CI/reviews | GitHub |
| Run deterministic source tests supported by GitHub Actions | GitHub Actions |
| Read Docker containers, systemd timers or local sensor/device state on RPi5 | Minimal RDC only with applicable authority and exception record |
| Replace a host-local file or restart a service | Minimal RDC only with separately exact LIVE authority |
| GitHub returns 403, 429, timeout, unknown write result, or owner authorization is missing | STOP, not RDC |
| A tool is inconvenient or GitHub is slower | GitHub |

## Scope and rollout

This is ordinary **GitHub-first tool priority**, **not** the separate `START <repo> GITHUB-ONLY` deferred-LIVE mode. This rule does not authorize source writes, merge, deploy, runtime changes, secret/permission changes, retry, rollback, or changes to repository settings. Stricter repository-local requirements win. A shared-policy PR/merge does not automatically amend or activate consumer repositories. Adopt the accepted immutable revision separately in each eligible repo's `AGENTS.md` and CI/routing contracts after local review; do not silently overwrite exclusions or trust boundaries.

Every host-required mixed workflow follows **GitHub -> minimal RDC -> GitHub**.
