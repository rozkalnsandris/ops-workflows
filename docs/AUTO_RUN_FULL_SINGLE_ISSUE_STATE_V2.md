# AUTO-RUN FULL single-issue normalized state v2

**Status:** shared source/governance contract; not active in consumers until explicit Slice E adoption  
**Canonical repository:** `rozkalnsandris/ops-workflows`  
**Tracking:** `#123`, roadmap `#119`, rollout `#124`  
**Related API write contract:** `docs/WRITE_PREFLIGHT_COMPACT_V1.md`

## 1. Purpose

This contract normalizes durable state for the existing **single-issue** AUTO-RUN FULL model.

The ownership rule is:

```text
target issue managed block = canonical run/work scope + current run phase
controller                 = minimal single-writer lock / active-run pointer
receipts/comments          = immutable or deterministic evidence only
GitHub                     = canonical durable continuation source
chat/session               = disposable
```

It does not activate AUTO-RUN FULL in a repository that does not already support it, does not widen source/merge authority, and does not activate Queue vNext `#96`.

## 2. Why normalization is needed

Historical consumer implementations may repeat the same mutable facts across the target issue, a controller issue/object, activation receipts, status comments and chat/session continuation.

Typical duplicated facts include:

- target issue identity and scope;
- active run identity;
- current phase;
- branch and PR pointers;
- attempt/correction counters;
- current blocker / owner gate;
- mutable CI/review snapshots;
- completion identities.

This creates extra reconciliation branches and drift risk. The v2 rule gives each durable fact one canonical owner wherever practical.

## 3. Canonical field ownership

| Fact | Canonical owner in v2 | Controller copy allowed? | Receipt copy allowed? |
| --- | --- | --- | --- |
| repository + target issue | target issue managed block | pointer only while ACTIVE/STOPPED | identity reference only |
| frozen source-scope digest | target issue managed block | only inside active-run digest | evidence reference only |
| run id | target issue managed block | pointer while ACTIVE/STOPPED | identity reference only |
| current phase | target issue managed block | **no** | **no** |
| branch / PR pointer | target issue managed block | **no** | historical evidence only |
| correction count | target issue managed block | **no** | **no** |
| current STOP reason | target issue managed block | **no** | optional immutable stop receipt |
| current owner gate | target issue managed block | **no** | **no** |
| mutable CI/review/mergeability | fresh GitHub read | **no** | do not persist refresh snapshots |
| exact completion main SHA | target issue completion summary | **no** | may be evidenced by one completion receipt |
| active target/run lock | controller | yes, canonical there | **no** |
| last deterministic controller transition id | controller | yes, canonical there | optional transition evidence |

Secrets, private runtime state, credentials, production configuration and ephemeral session state are forbidden from both managed blocks.

## 4. Target issue managed state

Canonical schema:

`policy/schemas/auto-run-full-single-issue-run-state-v2.schema.json`

Schema identity:

`rozkalns.auto-run-full-single-issue-run-state.v2`

Required top-level fields:

```text
schema
repository
issue_number
run_id
scope_digest_sha256
revision
phase
branch
pr_number
correction_count
stop_reason
owner_gate
completion
```

The state block belongs on the exact target issue (or one deterministic machine-managed surface attached to that issue). The body/Definition of Done remains the human work scope; the managed block does not replace the issue.

Phases:

```text
PLANNED
ACTIVE_SOURCE
PR_OPEN
WAITING_CI
READY
STOPPED
DONE
```

`revision` starts at `0` and increments by exactly one per accepted state transition. Updates must bind the expected current revision, run id and issue identity.

`correction_count` is bounded `0..2`; repository-local stricter limits win.

`owner_gate` may be `MERGE`, `LIVE`, `SCOPE_DECISION`, `REAUTHORIZATION`, or null. It records the current required gate; it is not authority by itself.

`STOPPED` requires an exact `stop_reason`. A wake event or CI completion must never silently clear it.

`DONE` requires a compact completion summary with the accepted exact main SHA and optional deterministic receipt reference.

## 5. Minimal controller

Canonical schema:

`policy/schemas/auto-run-full-single-issue-controller-v2.schema.json`

Schema identity:

`rozkalns.auto-run-full-single-issue-controller.v2`

The controller contains only:

```text
schema
repository
state
active_issue
active_run_id
active_run_digest_sha256
last_transition_id
```

Controller states:

```text
IDLE
ACTIVE
STOPPED
```

Rules:

- `IDLE` has no active issue/run/digest;
- `ACTIVE` binds exactly one target issue/run;
- a second issue cannot become ACTIVE while another live run is bound;
- `STOPPED` retains the exact active issue/run/digest;
- the controller never stores target issue title/body/DoD, current phase, branch, PR, CI history, review history, correction count or completion main SHA;
- stale run/digest writers fail closed.

The active-run digest is SHA-256 over canonical JSON:

```json
{
  "repository": "owner/repo",
  "issue_number": 123,
  "run_id": "uuid-v4",
  "scope_digest_sha256": "64-lowercase-hex"
}
```

## 6. State transitions

Allowed same-run target transitions:

```text
PLANNED -> ACTIVE_SOURCE
ACTIVE_SOURCE -> PR_OPEN
PR_OPEN -> WAITING_CI
WAITING_CI -> WAITING_CI   (only when correction_count increases by exactly 1)
WAITING_CI -> READY
READY -> DONE
```

Any non-`DONE` phase may transition to `STOPPED` with a non-empty reason. `STOPPED` is terminal for that run under this shared contract; it cannot be resumed by a wake event.

A fresh owner/repository-local decision may later start a **new run id** according to that repository's existing authority rules. State normalization never revives consumed authority.

Every transition validates:

- exact repository;
- exact target issue;
- exact run id;
- exact expected `revision`;
- active controller digest while controller state is ACTIVE;
- deterministic transition id.

An exact replay of an already-applied transition id with identical resulting state is an idempotent no-op. Reusing a transition id for different content, stale revision, stale run id or wrong issue is a conflict/STOP.

## 7. Controller activation and release

Controller activation:

```text
IDLE -> ACTIVE(exact issue, exact run, exact run digest)
```

Activation is eligible only for a fresh run whose target state is `PLANNED`.

If the exact controller binding already exists, `WRITE_PREFLIGHT_COMPACT` may reconcile it as already satisfied. A different live binding is a conflict and must STOP; do not overwrite, force-reset, invent another controller, or silently change target issue.

Successful release:

```text
target DONE + exact controller binding
-> controller IDLE
```

Aborted release is allowed only through an explicit repository-local abort/release decision after a `STOPPED` run. It is not an automatic cleanup path and is forbidden after ambiguous/consumed mutation failure unless that exact abort action is freshly authorized.

## 8. Receipts

Receipts are evidence, not mutable control state.

A receipt may contain:

- deterministic receipt identity;
- repository, issue number and run id reference;
- immutable transition/result identity;
- exact commit/main SHA evidence when terminal;
- timestamp / actor / workflow identity where useful.

A receipt must not become the canonical owner of:

- current phase;
- current branch/PR;
- correction budget;
- current CI/review/mergeability;
- current gate;
- current controller lock.

Do not create a receipt for every read-only CI/review refresh.

Historical receipts are preserved read-only during rollout; this contract does not delete or rewrite them.

## 9. Legacy read compatibility

Consumers have repository-local legacy controller formats. This shared contract therefore defines a **compatibility envelope**, not one invented universal legacy schema.

A consumer adapter may map its current legacy GitHub objects into these read-only components:

```text
legacy target scope object
legacy controller/run object
legacy activation receipt
legacy latest durable status/completion evidence
```

The shared compatibility reader cross-validates duplicated repository/issue/run/phase/PR identities. Exact agreement reconstructs a read-only v2 view. Any collision or disagreement fails closed.

Legacy state is never rewritten in place by Slice D. After Slice E adoption, **new activations use v2**; active/historical legacy runs remain readable audit history until their repository-local lifecycle ends.

## 10. Lost-session reconstruction

A new session reconstructs a normalized run using only:

```text
target issue managed state
controller state
fresh GitHub PR/CI/review facts only when required by the current phase
```

Chat history is not required.

Normal continuation needs two durable control objects instead of reconciling target + controller + activation receipt + mutable status receipt. Focused tests contain a synthetic legacy-vs-normalized fixture proving this object/read reduction and fewer duplicated mutable fields.

## 11. WRITE_PREFLIGHT_COMPACT integration

Slice C remains the only pre-dispatch object-write framework.

Before creating/updating target/controller/receipt state:

- exact existing identity + intended state -> reconcile/no-op;
- conflicting run identity -> STOP;
- stale revision/writer -> STOP;
- capability gap -> STOP rather than broad scan;
- mutation dispatch still consumes authority according to repository-local rules.

This contract does not create retry, rollback, cleanup or merge authority.

## 12. Authority and safety invariants

Normalization does not change:

- repository-local FULL activation requirements;
- exact issue scope;
- merge authority;
- merge != LIVE;
- LIVE/deploy/runtime/DB/data/secrets/credentials/permissions/settings boundaries;
- first-mutation authorization consumption;
- post-dispatch ambiguity fail-closed behavior;
- three-attempt / stricter repository-local limits;
- GitHub as canonical mutable state source.

Queue v1/A1 and Queue vNext `#96` remain inactive under their existing prerequisites. A future Queue implementation may reuse the target-issue managed-state ownership pattern, but Slice D does not change Queue schemas, authority or activation.

## 13. Rollout

This shared source contract becomes consumer behavior only through Slice E `#124`, one repository at a time.

For a supporting consumer:

1. preserve historical/active legacy state;
2. add v2 validator/schema support;
3. use v2 only for a fresh new activation;
4. keep repository-local stricter authority rules;
5. prove lost-session reconstruction and stale-writer rejection;
6. record exact accepted main/CI evidence.

Repositories without single-issue FULL support record the capability as not applicable; they do not create a controller for uniformity.
