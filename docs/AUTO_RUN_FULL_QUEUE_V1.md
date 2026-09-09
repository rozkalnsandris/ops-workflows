# AUTO-RUN FULL Queue v1 — shared source and migration contract

**Status:** A1 shared source-policy design; not active in consumers  
**Canonical repository:** `rozkalnsandris/ops-workflows`  
**Tracking issue:** `rozkalnsandris/ops-workflows#39`  
**Machine contract:** `policy/auto-run-full-queue-v1.json`

## 1. Purpose

AUTO-RUN FULL Queue v1 increases throughput without introducing concurrent source writers in one repository.

The target operator experience is one explicitly scoped queue activation containing up to ten named issues. The controller processes exactly one issue at a time through the normal source/PR/CI/review/merge lifecycle, then advances to the next frozen issue automatically.

The target end state is:

```text
frozen issue queue
-> one issue ACTIVE
-> source / tests / Draft PR / CI / review / bounded corrections
-> exact-head merge
-> exact-main verification
-> next frozen issue
-> all source items complete
-> final exact-main read-only preflight / reconciliation
-> no live change: DONE
   or
-> one final owner LIVE decision
-> fixed reviewed repository-specific rollout
-> final receipt
```

This A1 document defines shared source policy only. It does not activate the command, grant queue-wide source/merge authority, enable an executor, migrate a consumer, or authorize a live mutation.

## 2. Compatibility-first migration

Existing repository-local AUTO-RUN FULL implementations remain authoritative until each consumer explicitly adopts a future completed Queue contract.

A shared-policy merge in `ops-workflows` must not change consumer behavior by itself.

A consumer remains on its existing mode when any of these are true:

- no explicit Queue adoption manifest/caller exists;
- the consumer has not pinned an accepted `ops-workflows` commit SHA;
- repository-local rules have not been reconciled;
- the canary/adoption acceptance gate has not completed.

During migration:

- old AUTO-RUN FULL remains usable;
- FAST-LANE v2.2 remains usable;
- `GITHUB-ONLY / LIVE-ALL` compatibility artifacts are preserved;
- Auto-Live v1 is reconciled deliberately rather than silently replaced;
- repository-local stricter trust-boundary rules always win.

## 3. Queue identity and scope

A Queue activation must freeze an ordered explicit list of issue numbers.

Initial design limit:

```text
1 <= queue_length <= 10
```

The queue never means:

- all open issues;
- all issues with a label;
- all future issues;
- a repository-wide autonomous backlog.

Issues created or edited after activation do not implicitly join the queue or widen its authority.

Each queued issue remains a normal independent GitHub work item with its own:

- repository and issue number;
- Definition of Done;
- source branch;
- canonical PR;
- exact PR head SHA;
- CI/review state;
- merge result;
- exact post-merge main identity.

## 4. One active issue

At most one queued issue may be `ACTIVE` for one repository controller at a time.

The controller is an orchestration pointer, not a replacement for issue/PR state.

A deterministic source state model should remain coarse, for example:

```text
IDLE
QUEUE_ACTIVATING
WORKING
WAITING_CI
WAITING_REVIEW
CORRECTING
VERIFYING_MERGE
ADVANCING
QUEUE_SOURCE_COMPLETE
PAUSED_EXTERNAL
PAUSED_OWNER_LIVE_GATE
STOP_SCOPE_OR_RISK
STOP_ERROR
DONE
```

The exact final state names may evolve before activation, but the following invariants may not:

- one active issue;
- GitHub-canonical continuation;
- explicit frozen order;
- deterministic next-item transition;
- fail closed on ambiguous scope/order/state.

GitHub Actions runner queues or concurrency groups may optimize execution, but they are not the canonical issue ordering authority.

## 5. Per-issue source cycle

Each queued issue should use the existing disciplined lifecycle:

```text
fresh canonical state
-> branch
-> smallest coherent source/docs/tests change
-> focused validation
-> Draft PR
-> exact-head CI/review
-> bounded scope-preserving correction
-> frozen exact head
-> guarded merge
-> exact-main verification
```

Routine CI polling, review ingestion, GET/read-only evidence refresh, diff inspection and other technical checkpoints are not new owner gates.

The controller advances only after the current issue has a proven successful source terminal state.

A failed or ambiguous current issue must not be skipped merely to keep the queue moving.

## 6. Queue activation authority — design boundary

The desired future UX is one explicit Queue activation for the frozen issue set.

A future Queue command may be designed to freeze source + merge authority for every named issue, but that is a trust-boundary change from issue-scoped AUTO-RUN FULL v2 and therefore requires an explicit reviewed machine contract before use.

A1 does **not** grant that authority.

Until later source work explicitly activates Queue authorization semantics:

- existing AUTO-RUN FULL authorization rules remain authoritative;
- Queue documentation/controller state is evidence only;
- a queue cannot infer authority from an issue list, label, prior command, chat history or controller pointer;
- Queue authority is never LIVE authority.

## 7. Scope and drift behavior

The frozen queue must fail closed when any queued item develops a material change in:

- Definition of Done;
- repository;
- trust boundary;
- required mutation class;
- dependency ordering;
- repository rules/policy compatibility.

Main drift between issue cycles is expected and must be freshly resolved before activating the next item.

Within one active issue, exact-head and exact-main controls remain required by the consumer's active AUTO-RUN FULL/FAST policy.

No controller may silently reinterpret a frozen issue as broader work.

## 8. Resume model

GitHub is the canonical continuation store.

Preferred future resume:

1. GitHub event-triggered Work task for relevant PR activity when configured;
2. consolidated scheduled watchdog only as fallback;
3. manual continuation may resume the already-authorized current queue, but never creates new Queue, merge or LIVE authority.

A session ending is not itself an owner gate.

## 9. Final source reconciliation

After the final frozen issue is merged and exact-main verified, the controller must perform a final source/read-only reconciliation before any LIVE question:

- read current exact `main`;
- verify required exact-SHA CI;
- classify whether a live change is required;
- collect all obtainable GET/SELECT/read-only target/baseline evidence;
- determine the exact fixed rollout/operation identity for that consumer.

If no production/runtime mutation is required, the queue may finish `DONE` without asking for LIVE.

If live mutation is required, the queue stops once at the final owner LIVE gate.

## 10. Simple LIVE — one decision, fixed reviewed rollout

The preferred LIVE model is intentionally simpler than a generic transaction engine.

The owner approves one exact, already-reviewed rollout identity bound to:

- exact approved Git SHA;
- exact target/environment/device alias;
- expected baseline where practical;
- fixed repository-specific operation/workflow identity;
- explicit exclusions.

The detailed technical sequence lives in reviewed source/workflows. The owner authorization does not need to carry a dynamically invented list of shell commands or arbitrary operation graph.

A typical fixed rollout may perform, as applicable:

```text
read-only preflight
-> final SHA/target/baseline revalidation
-> acquire per-target concurrency ownership
-> deterministic build / exact candidate preparation
-> verify exact candidate identity
-> bounded deploy/activation through the reviewed adapter
-> read-only postconditions / reconciliation
-> final receipt
```

For Cloudflare Workers, prefer immutable version identity and deploy/promote the same verified version rather than rebuilding between verification and production deployment.

Do not add gradual deployment/canary state by default. A consumer may require it only when its own reviewed risk classification says so.

## 11. LIVE failure semantics

Before the first state-changing operation, failures are fail-closed with zero production mutation.

The LIVE authorization is consumed when the first authorized mutation starts.

After that point, any error, ambiguity, SHA/target/baseline drift, new risk class or inability to prove state means:

```text
preserve public-safe evidence
-> STOP
```

Default behavior is not automatic:

- retry;
- rollback;
- cleanup;
- alternate deployment path;
- undeclared follow-up mutation.

Those behaviors require a separately reviewed/predeclared contract when ever allowed.

## 12. Target serialization

At most one mutation-capable rollout may own a production target at a time.

Use a stable target concurrency key or an equivalent trusted-runtime lock.

Concurrency prevents simultaneous writers; it does not replace exact baseline revalidation immediately before mutation.

## 13. Shared and consumer boundaries

### `ops-workflows`

May own:

- normative Queue policy;
- machine-readable invariants;
- schemas and validation tooling;
- reusable GitHub-side guard workflows;
- migration/adoption policy;
- Simple LIVE shared guard contract;
- compatibility and deprecation records.

It must not become:

- a production credential store;
- a generic production executor;
- an RPi5 root/sudo/systemd helper;
- a database apply implementation;
- an arbitrary SSH/remote-shell bridge.

### Consumer repository

Owns:

- explicit Queue adoption manifest/caller;
- immutable pin to the accepted shared contract;
- repository-specific deploy classification;
- fixed rollout adapter/entrypoint;
- target/environment mapping;
- least-privilege credentials and environment controls;
- stricter local rules.

### `RPi5_main`

Remains the trusted host/runtime boundary for RPi5-specific execution.

A shared Queue/LIVE policy may coordinate a bounded handoff, but does not move privileged host authority into `ops-workflows`.

## 14. Consumer adoption sequence

Recommended migration sequence:

```text
1. merge shared Queue docs/policy/tests in ops-workflows
2. keep legacy AUTO-RUN FULL active everywhere
3. finish Queue controller/authorization source contracts
4. choose one canary consumer
5. consumer adoption PR pins an immutable ops-workflows SHA
6. prove Queue behavior source-only
7. prove final Simple LIVE path under the consumer's existing trust boundary
8. explicitly mark the consumer migrated
9. repeat one consumer at a time
10. deprecate legacy AUTO-RUN FULL only after intended migrations are proven
```

No consumer is migrated by inference.

## 15. A1 acceptance criteria

A1 is complete when:

- this normative design exists;
- machine invariants encode the compatibility, queue and LIVE boundaries;
- CI fails if those invariants drift;
- README/AGENTS clearly state that Queue is source-policy design only;
- old AUTO-RUN FULL remains the active consumer behavior;
- no consumer/runtime/LIVE mutation is introduced.

Later implementation phases may add controller state, schemas, event resume, reusable guards, canary adoption and live acceptance. Those later phases must preserve the A1 compatibility boundary until explicit consumer migration.