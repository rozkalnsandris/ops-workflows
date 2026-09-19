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
