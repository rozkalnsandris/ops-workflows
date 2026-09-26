# WRITE_PREFLIGHT_COMPACT v1

Status: ACTIVE normative appendix to `docs/GITHUB_API_ACCESS_V1.md`  
Canonical repository: `rozkalnsandris/ops-workflows`  
Tracking issue: `ops-workflows#122`

## Contract relationship

This document is a **normative appendix of `GITHUB_API_ACCESS_V1`**, not a competing API-access framework.

It governs only predictable GitHub object-state validation immediately before an already-authorized create/update write. The parent contract remains authoritative for request discipline, rate limits, `FINAL_PREMERGE_COMPACT`, mutation authorization consumption, post-dispatch ambiguity, reconciliation, and `EXACT_MAIN_MINIMAL`.

`WRITE_PREFLIGHT_COMPACT` never grants source, merge, LIVE, deployment, retry, rollback, cleanup, secrets, permissions, settings, or production-data authority.

## Why this exists

GitHub documents conflict/validation outcomes such as `409` and `422` for object creation. GitHub REST best practices also recommend serial requests, targeted reads, avoiding repeated validation errors, and filtering list operations to the smallest useful scope.

The objective is to prevent **predictable** invalid or duplicative dispatches when current canonical state can determine the result before the mutation call starts. Unexpected API failures remain failures and are handled by the parent mutation-boundary contract.

## Budget class

`WRITE_PREFLIGHT_COMPACT` is a qualitative read budget used immediately before an object create/update dispatch when predictable object-state validation is relevant.

Rules:

- serial, minimum-sufficient, targeted reads only;
- reuse same-step evidence when it already proves the needed fact;
- do not enumerate unrelated issues, PRs, branches, comments, controllers, receipts, or history;
- do not switch tools/endpoints/accounts/tokens to obtain a broader duplicate search;
- if a required capability is unavailable and correctness cannot be proven from already-held canonical evidence, return `WRITE_PREFLIGHT_CAPABILITY_UNAVAILABLE` and STOP;
- a read-only rejection or no-op before dispatch does not consume mutation authority under contracts that consume authority only when dispatch starts.

## Stable dispositions

```text
WRITE_PREFLIGHT_ELIGIBLE
WRITE_PREFLIGHT_ALREADY_SATISFIED
WRITE_PREFLIGHT_CONFLICT
WRITE_PREFLIGHT_INVALID_HEAD_BASE
WRITE_PREFLIGHT_DUPLICATE_EXACT_RECONCILED
WRITE_PREFLIGHT_DUPLICATE_CONFLICT
WRITE_PREFLIGHT_AUTHORITY_DRIFT
WRITE_PREFLIGHT_CAPABILITY_UNAVAILABLE
```

Interpretation:

- `WRITE_PREFLIGHT_ELIGIBLE` — current canonical evidence permits the planned mutation to be dispatched under already-existing authority.
- `WRITE_PREFLIGHT_ALREADY_SATISFIED` — the target already has the exact intended state; do not dispatch.
- `WRITE_PREFLIGHT_DUPLICATE_EXACT_RECONCILED` — an exact durable object already exists and its canonical identity should be reused; do not dispatch.
- all other dispositions reject dispatch and require correction, fresh authority, or STOP as appropriate.

## Operation profiles

### Create branch/ref

Bind exact repository, ref name, and source SHA.

Targeted preflight:

1. determine whether the exact ref exists when the available connector supports the lookup;
2. absent + bindings valid -> `WRITE_PREFLIGHT_ELIGIBLE`;
3. present at exact intended SHA + operation declared idempotent -> `WRITE_PREFLIGHT_ALREADY_SATISFIED`;
4. present at another SHA -> `WRITE_PREFLIGHT_CONFLICT`.

Never force-update, delete, rename, recreate, or invent an alternate branch as recovery.

### Create pull request

Bind exact repository, base, head, and intended head/base relationship.

Targeted preflight:

1. prove head/base identity when the available connector permits;
2. prove an eligible base..head diff when practical;
3. query only for an existing PR matching the intended head/base scope;
4. no existing PR + valid non-empty diff -> `WRITE_PREFLIGHT_ELIGIBLE`;
5. exact existing PR -> `WRITE_PREFLIGHT_DUPLICATE_EXACT_RECONCILED` and reuse its canonical PR identity;
6. conflicting existing PR, missing head/base, or no eligible diff -> reject before dispatch.

Never invent a substitute branch or PR to bypass the rejection.

### Durable issue/controller/receipt object

Only automation contracts that declare duplicate objects unsafe require deterministic identity.

The object must carry a stable machine identity marker in a supported durable field. Search only the expected object scope.

- no object with that identity -> `WRITE_PREFLIGHT_ELIGIBLE`;
- exact identity + exact protected payload/state -> `WRITE_PREFLIGHT_DUPLICATE_EXACT_RECONCILED`;
- same identity + conflicting protected payload/state -> `WRITE_PREFLIGHT_DUPLICATE_CONFLICT`.

Ordinary human planning issues do not gain mandatory idempotency from this appendix.

### Durable comment/receipt

When duplicate comments would corrupt or confuse state, bind a deterministic receipt identity and inspect only the relevant issue/PR thread.

- absent -> `WRITE_PREFLIGHT_ELIGIBLE`;
- exact receipt -> `WRITE_PREFLIGHT_DUPLICATE_EXACT_RECONCILED`;
- same identity but conflicting receipt -> `WRITE_PREFLIGHT_DUPLICATE_CONFLICT`.

Do not enumerate unrelated repository comments or history.

### Update issue/PR metadata

Bind exact object identity and only the intended fields.

- already at intended state -> `WRITE_PREFLIGHT_ALREADY_SATISFIED`;
- intended delta remains safe -> `WRITE_PREFLIGHT_ELIGIBLE`;
- conflicting state or risk expansion -> `WRITE_PREFLIGHT_CONFLICT`.

Prefer additive/removal operations when that is the intended semantic. Do not accidentally replace full label/assignee sets.

### Merge

Merge is explicitly **out of scope** for this appendix. It continues to use the parent `GITHUB_API_ACCESS_V1` `FINAL_PREMERGE_COMPACT` contract plus repository-local authority.

## Authority and dispatch boundary

Preflight is read-only validation, not authorization.

```text
already-authorized operation
-> WRITE_PREFLIGHT_COMPACT
-> eligible?
   yes -> dispatch exactly the already-authorized mutation
   exact no-op/reconciled -> do not dispatch
   conflict/invalid/capability/authority drift -> STOP or correct under existing rules
```

No preflight disposition creates a retry. Once a mutation call is dispatched, the parent mutation-boundary rules take over immediately. A post-dispatch `429`, timeout, transport error, malformed/partial response, or uncertain outcome is never converted into permission to run preflight and dispatch again.

## Capability honesty

A connector may not expose every narrow lookup or filter. Missing capability does not permit broad scanning or quota-bypass behavior.

If already-held canonical evidence is sufficient, reuse it. Otherwise return `WRITE_PREFLIGHT_CAPABILITY_UNAVAILABLE` and STOP before dispatch.

## Deterministic acceptance scenarios

The focused model/tests cover:

1. absent branch -> eligible create;
2. exact branch SHA -> no-op when idempotent;
3. conflicting branch SHA -> reject without force/delete/recreate;
4. exact existing PR -> canonical PR reuse;
5. invalid/missing/no-diff PR head/base -> reject;
6. exact durable identity -> reconcile;
7. durable identity collision -> reject;
8. metadata already intended -> no-op;
9. authority/state drift -> reject before dispatch;
10. post-dispatch ambiguity remains governed by the parent mutation boundary and never permits duplicate dispatch;
11. missing capability -> STOP without broad search or alternate-tool bypass;
12. merge continues to use `FINAL_PREMERGE_COMPACT`.

## Compatibility

This appendix does not change:

- GitHub as canonical mutable-state source;
- serial/minimum-sufficient retrieval;
- `FINAL_PREMERGE_COMPACT`;
- explicit MERGE by default and repository-local FULL exceptions;
- merge/LIVE separation;
- authorization consumption at mutation dispatch;
- post-dispatch fail-closed behavior;
- no automatic retry/rollback/cleanup/alternate mutation path;
- repository-local stricter rules.
