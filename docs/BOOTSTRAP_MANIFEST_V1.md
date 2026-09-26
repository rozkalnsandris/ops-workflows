# BOOTSTRAP_MANIFEST_V1

Status: ACTIVE shared routing contract  
Canonical repository: `rozkalnsandris/ops-workflows`  
Tracking: `ops-workflows#120`

## Purpose

`BOOTSTRAP_MANIFEST_V1` defines one small, machine-readable repository routing surface for normal agent bootstrap. Its goal is to reduce repeated parsing of large repository-specific rule files when the immediate bootstrap question is only:

- where are the normative local rules;
- where are the shared work-cycle/API-access rules;
- where is the stable continuation locator;
- which automation modes are supported;
- which deployment-routing profile applies.

The manifest is an optimization layer only. It is **not** canonical mutable state and it is never an authorization source.

Canonical default path:

```text
.github/agent-bootstrap.json
```

## Precedence

When sources disagree, use this order:

```text
repository-local normative rules
-> shared normative policy
-> bootstrap manifest routing metadata
```

The manifest may point to stricter rules. It can never weaken, replace, or override them.

## Manifest shape

Canonical schema identity:

```text
rozkalns.agent-bootstrap.v1
```

Required top-level fields:

```text
schema
repository
shared_policy
rules
continuation
automation
deployment_profile
```

Example:

```json
{
  "schema": "rozkalns.agent-bootstrap.v1",
  "repository": "rozkalnsandris/example",
  "shared_policy": {
    "work_cycle": "docs/AGENT_WORK_CYCLE_V1.md",
    "github_api_access": "docs/GITHUB_API_ACCESS_V1.md"
  },
  "rules": {
    "primary": "AGENTS.md",
    "local_strict_rules": [
      "AGENTS.md#scope-boundary"
    ]
  },
  "continuation": {
    "kind": "issue",
    "locator": "38"
  },
  "automation": {
    "fast_lane": true,
    "auto_run_full": true,
    "queue_mode": "inactive"
  },
  "deployment_profile": "source-only"
}
```

The schema is intentionally narrow and rejects unknown fields.

## Stable routing metadata only

Allowed content is repository configuration that remains meaningful across ordinary commits, such as:

- repository identity;
- rule-file paths;
- stable section locators for local stricter rules;
- stable canonical continuation issue/file locator;
- whether FAST-LANE or single-issue AUTO-RUN FULL is supported;
- whether Queue mode is inactive, supported, or not applicable;
- routing-only deployment profile.

A continuation issue locator is valid only when the issue itself is the repository's stable canonical continuation/handoff identity. It must not be changed merely to point at the latest transient work item.

## Forbidden mutable truth

The manifest must never become a cache for mutable operational state. Do not persist values such as:

- current `main`, branch, or PR head SHA;
- transient active PR number;
- CI/check state;
- review state or mergeability;
- runtime/deployed revision;
- one-time merge or LIVE authorization;
- authorization-consumed state;
- secrets, credentials, tokens, passwords, or API keys.

Current mutable facts are still read freshly from their canonical source when the selected lane needs them.

## Resolution semantics

Normal bootstrap with an adopted manifest is:

```text
read .github/agent-bootstrap.json
-> validate schema + referenced canonical surfaces
-> resolve local rules + shared-policy routes + stable continuation locator
-> read current default-branch identity
-> execute GITHUB_API_ACCESS_V1 BOOTSTRAP_MINIMAL for one current lane
```

The manifest reduces routing discovery. It does not satisfy the fresh mutable-state reads required by `BOOTSTRAP_MINIMAL`.

### Manifest absent

Absence is backward compatible:

```text
manifest absent
-> use existing repository-local AGENTS.md/startup routing
-> no authority change
```

### Manifest invalid or stale

If the manifest is malformed, contains forbidden/unknown fields, references a missing canonical file, or otherwise cannot be trusted:

```text
unambiguous repository-local rules exist
-> ignore manifest optimization
-> fall back to repository-local rules

repository-local routing is also ambiguous
-> STOP_AMBIGUOUS
```

Never choose the less strict interpretation.

## Continuation kinds

Supported continuation routing kinds:

- `issue` — stable canonical issue number encoded as a string;
- `file` — stable repository-relative continuation/handoff file;
- `none` — the repository intentionally has no stable continuation surface.

The locator is routing metadata. The mutable body/state of the issue or file must still be read when required.

## Automation routing

The `automation` block is descriptive capability routing only:

- `fast_lane` — repository supports the shared FAST-LANE vocabulary;
- `auto_run_full` — repository supports a repository-local single-issue FULL mode;
- `queue_mode` — `inactive`, `supported`, or `not-applicable`.

A boolean or queue-mode value does not activate the mode and does not grant source, merge, LIVE, retry, rollback, cleanup, settings, or credential authority.

## Deployment profile

`deployment_profile` is routing metadata only:

- `simple-deploy`
- `github-only`
- `source-only`
- `custom`
- `none`

It does not activate a deployment mechanism or alter any production gate.

## Validation

Canonical machine surfaces:

```text
policy/agent-bootstrap-v1.json
policy/schemas/agent-bootstrap-v1.schema.json
scripts/agent_bootstrap_manifest.py
```

The validator checks:

- exact allowed fields;
- safe repository-relative paths;
- stable continuation form;
- supported automation/deployment values;
- forbidden mutable/secret-like keys;
- existence of referenced canonical files when a repository root is supplied.

A valid manifest may route bootstrap; an invalid manifest may only cause fallback or STOP.

## Relationship to Agent Work Cycle v1

`docs/AGENT_WORK_CYCLE_V1.md` remains normative for `START`, `SYNC`, `turpini`, owner gates, fail-closed behavior, and terminal response semantics.

This contract changes only bootstrap routing discovery. Slice B (`ops-workflows#121`) separately defines the planned START safe auto-continuation wording.

## Relationship to GitHub API Access v1

`docs/GITHUB_API_ACCESS_V1.md` remains normative for request budgets and freshness. The manifest is read before or as part of `BOOTSTRAP_MINIMAL` routing, but it never permits cached mutable SHA/PR/CI/review/runtime/authorization state to replace fresh canonical reads.

## Security and authority

This contract grants no merge, LIVE, deployment, runtime, DB/data, secrets, credentials, permissions, settings, retry, rollback, cleanup, Queue activation, or trust-boundary authority.

Repository-local stricter rules always win.

## Rollout

`ops-workflows` is the first canonical manifest.

Consumer rollout is intentionally deferred to FAST-LANE v2.3 Slice E (`ops-workflows#124`) after Slices A–D are accepted. Missing manifests remain supported until a repository explicitly adopts this contract.
