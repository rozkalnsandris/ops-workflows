# Dependency and workflow hardening v1

## Purpose

This contract adds two GitHub-side maintenance layers without changing the repository's merge, LIVE, credential, permission, or runtime authority model:

1. **Renovate** proposes bounded GitHub Actions and reusable-workflow dependency update PRs.
2. **actionlint + zizmor** statically validate GitHub Actions workflow correctness and security.

GitHub remains canonical. Repository-local stricter rules remain authoritative.

## Renovate operating model

The repository config is `renovate.json` and is intentionally limited to the `github-actions` manager.

Required behavior:

- external Actions and reusable workflows remain pinned to full 40-character commit SHAs;
- a verified version/ref comment is retained beside each digest so Renovate can resolve and update the pin;
- `helpers:pinGitHubActionDigests` is enabled;
- Renovate never automerges and platform-native automerge is disabled;
- at most two Renovate branches/PRs are open concurrently;
- at most one new PR is created per hour and at most two Renovate commits are created per hour;
- automatic rebasing is limited to conflicts;
- GitHub vulnerability-alert PR handling is explicitly disabled in this first slice so the scope stays GitHub-Actions-only and cannot bypass the normal Renovate rate/concurrency lane;
- Dependency Dashboard approval is the fail-closed default for every GitHub Actions update; only the explicitly named `digest`, `patch`, and `minor` update types may bypass it and be grouped to reduce CI noise;
- major GitHub Actions updates require explicit Dependency Dashboard approval before Renovate opens the PR. `prCreation` remains `immediate`: Renovate's documented approval gate is `dependencyDashboardApproval`, which must not be combined with `prCreation: "approval"`;
- GitHub-hosted runner labels (`github-runner`, including Ubuntu labels) are disabled for this canary slice until actionlint and repository contracts intentionally support an update;
- `zizmorcore/zizmor-action` and its separate `ghcr.io/zizmorcore/zizmor` `uses-with` engine input are both disabled for Renovate. A zizmor update must be a manual companion change that updates the action SHA/ref, exact supported engine version, machine policy, and this documentation together; this preserves exact pinning while preventing an intentionally invalid partial Renovate PR;
- Renovate PRs are ordinary reviewable source PRs and are never merge authority.

Dependency Dashboard approval is a creation gate. It does not retroactively close a major Renovate PR that existed before this policy was active, and a green CI result on such a PR is not Dashboard approval. That stale PR remains an explicit reconciliation decision; when manual close is forbidden, it must remain open and must not be silently reinterpreted as approved or merge-ready.

The hosted Mend Renovate GitHub App is the intended executor. **Installing or authorizing that app is a separate owner repository-permission action.** Committing this config does not install the app and does not grant repository settings or permissions authority.

## Digest tracking convention

Renovate cannot reliably map an arbitrary bare SHA back to a release/tag. Digest-pinned Action references therefore use the form:

```yaml
uses: owner/action@0123456789abcdef0123456789abcdef01234567 # v1.2.3
```

The SHA remains the executable identity; the trailing version/ref is tracking metadata for dependency maintenance.

## Reusable workflow static analysis

Canonical reusable workflow:

`.github/workflows/workflow-security.yml`

It is designed to be called by consumers only through a reviewed exact `ops-workflows` commit SHA.

### actionlint

- version: `1.7.12`;
- Linux amd64 release archive SHA-256 is fixed in source;
- the archive is downloaded over HTTPS and verified before execution;
- actionlint scans the caller repository's GitHub Actions workflows;
- no workflow file is modified.

### zizmor

- `zizmorcore/zizmor-action` is pinned to exact commit `3dc1ecc9bcb9e94e9b2c709687979e1298497054` (`v0.6.2`);
- the action is also told to run exact supported zizmor engine version `1.29.0` rather than its mutable `latest` alias;
- Renovate does not update this action or its `ghcr.io/zizmorcore/zizmor` `uses-with` engine input independently: its reviewed maintenance unit is the action/ref, engine, policy, validator expectation, and this documented compatibility statement;
- collection is limited to workflows;
- online audits are disabled;
- regular persona with medium severity/confidence floor is used to keep the first shared gate focused;
- Advanced Security/SARIF upload is disabled, so `security-events: write` is not required;
- GitHub annotations are enabled;
- auto-fix is not allowed.

## Permission and execution boundary

The reusable workflow:

- uses only GitHub-hosted `ubuntu-24.04` runners;
- declares only `contents: read`;
- does not inherit caller secrets;
- does not write repository content, issues, PRs, settings, or security events;
- does not execute production/LIVE/runtime mutation;
- does not become a deployment executor.

The existing `public-repo-baseline.yml` remains authoritative for full-SHA pinning, no `permissions: write-all`, and public self-hosted runner restrictions.

## Adoption

`ops-workflows` validates this contract on its own PRs through `.github/workflows/dependency-workflow-hardening-contract.yml`.

A consumer may later opt in with an exact immutable reference, for example:

```yaml
jobs:
  workflow-security:
    uses: rozkalnsandris/ops-workflows/.github/workflows/workflow-security.yml@<exact-40-character-sha>
```

Consumer adoption is explicit. A shared `ops-workflows` merge never auto-enrolls another repository.

## Owner gates

This source contract does not change existing owner gates:

- merge remains explicit unless a repository-local activated FULL/Queue contract says otherwise;
- Renovate App installation/permission changes require an explicit owner action;
- merge never authorizes LIVE;
- production/runtime/credential/permission changes remain separately gated.

## Rollout continuity snapshot — 2026-09-19

This section is a public-safe continuity snapshot for the Mend Renovate / workflow-security rollout. It is intentionally concise and does not replace fresh GitHub reads. **Before continuing any repository, re-read that repository's current rules, current `main`, exact PR HEAD, exact-head checks, reviews and unresolved threads.** Mutable state below is a handoff aid, not long-lived truth or authorization.

### Selected Mend repositories

The owner selected these 11 repositories for the hosted Mend Renovate GitHub App:

- `ops-workflows`
- `rozkalns-control-center`
- `rozkalns_weather`
- `RPi5_main`
- `RPi5-maintenance`
- `balcony-irrigation-esp32`
- `home-assistant-config`
- `dashboard_RPi5`
- `rozkalns-cv`
- `hermes-tech`
- `hermes-deals`

The shared consumer baseline used during this rollout is immutable `ops-workflows@0450e662093c41e98ca96802b523ac91eb02e5fe`. Consumer callers use `contents: read`, no secret inheritance, GitHub-hosted `ubuntu-24.04`, actionlint `1.7.12`, and zizmor action `3dc1ecc9bcb9e94e9b2c709687979e1298497054` with engine `1.29.0`.

### Completed / merged consumers

- `rozkalns-control-center` PR `#736` merged; squash/main commit `af18c864cb25cdb2283a95a80c88e1999a255713`.
- `rozkalns_weather` PR `#139` merged; squash/main commit `9e903b0e1d129856c4b1533b48487b7f5c36737d`.
- `RPi5_main` PR `#627` merged; squash/main commit `0a28218ecb832ba8162c00f54f5d7deaccd0c17a`.
- `hermes-tech` PR `#154` merged; squash/main commit `4068240c1783b255f58e2490f2d62440abae3866`.
- `ops-workflows` remains the accepted shared canary/baseline at `0450e662093c41e98ca96802b523ac91eb02e5fe`; no artificial consumer-rollout source change was required there.

### Remaining Draft PRs at snapshot time

| Repository | PR | Exact HEAD | Snapshot CI state |
| --- | ---: | --- | --- |
| `RPi5-maintenance` | `#34` | `cff1898953bdc16432e0ca3c98b88695ec29fa4f` | `validate` SUCCESS; `Workflow security` SUCCESS |
| `balcony-irrigation-esp32` | `#52` | `e9caa3a53cbd93ec4ceb7ec7d78ef5577d0dd727` | `firmware-ci` SUCCESS; `Workflow security` SUCCESS; `GITHUB-ONLY` SUCCESS |
| `home-assistant-config` | `#147` | `7f24345bac9ac2f4558eee4891d8f94652c63a3b` | `validate` SUCCESS; `Workflow security` SUCCESS; `GITHUB-ONLY` SUCCESS |
| `dashboard_RPi5` | `#274` | `3a2b2879ecfef3d47a146b449488913f7fc6a8cb` | `CI` SUCCESS; `Workflow security` SUCCESS; `FAST-LANE` SUCCESS; `GITHUB-ONLY` SUCCESS |
| `rozkalns-cv` | `#483` | `48c5128b577dd469ca083d3df23bfaf01db55d47` | `CI`, `Workflow security`, `PDF quality`, `Browser lab synthetic stability`, `CodeQL Evidence`, `GITHUB-ONLY` all SUCCESS |
| `hermes-deals` | `#917` | `fd28e805372b23658af501f51dffbde507c8a70a` | `GITHUB-ONLY` SUCCESS; queue adoption guard SUCCESS; `Workflow security` FAILURE; repository CI FAILURE |

The first five remaining PRs above had green exact-head workflow evidence at snapshot time, but they are still Draft. Do not mark Ready or merge from this table alone: refresh current `main`, mergeability, exact-head checks, reviews and unresolved threads first.

### `hermes-deals` blocker evidence

`hermes-deals #917` is the current non-green consumer and must remain fail-closed until its existing workflow findings are reconciled rather than suppressed.

At exact HEAD `fd28e805372b23658af501f51dffbde507c8a70a`, shared Workflow security run `35442132761` failed in **both** actionlint and zizmor. Actionlint currently reports, among other findings:

- repository-specific self-hosted labels such as `hermes-deals-audit` and `hermes-deals-release` are unknown to actionlint without an explicit repository label configuration;
- multiple existing ShellCheck findings including `SC2024`, `SC2251`, `SC2015`, `SC2006`, and `SC2034` across existing workflows.

The repository's own CI run `35442132507` also failed on the same PR snapshot. A new session must freshly inspect both failing lanes, determine the smallest policy-correct remediation, and must not silence findings merely to obtain green CI. Self-hosted runner semantics and the production/host trust boundary must remain repository-local and must not be moved into `ops-workflows`.

### `hermes-tech` Actions-policy lesson

`hermes-tech` initially produced a reusable-workflow `startup_failure` even though the caller YAML matched consumers where the scan worked. The cause was the repository's restrictive GitHub Actions policy: the shared workflow uses the external action

`zizmorcore/zizmor-action@3dc1ecc9bcb9e94e9b2c709687979e1298497054`.

The owner fixed the repository setting by adding that exact action SHA to the selective allowlist while retaining GitHub-created Actions permission and full-length SHA enforcement; broad `Allow all actions` / verified-creator expansion was not required. Because the new workflow existed only on the PR branch, the prior startup-failed run could not be usefully rerun through the available failed-job mechanism. Closing and reopening the PR generated a fresh `pull_request.reopened` run, after which `Workflow security`, repository CI and GITHUB-ONLY all succeeded. This was a repository Actions-policy fix, not a shared-workflow source workaround.

### Continuation contract

For the next chat/session, the intended rollout continuation is the six remaining Draft PRs above, beginning with a fresh repository-local START/SYNC and proceeding source-only to Ready/STOP. Recommended first lane: `START RPi5-maintenance`.

This snapshot grants **no** merge, repository-settings, permission, secrets, LIVE, deploy, host/runtime, device, Home Assistant, Cloudflare, database, or production-data authority. Merge remains an explicit owner decision per repository. Mend App scope/settings changes remain owner-controlled. Any current SHA/check/review/authorization state must be refreshed from GitHub before use.
