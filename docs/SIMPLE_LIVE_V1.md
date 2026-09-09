# Simple LIVE v1 — owner-driven final rollout contract

**Status:** A5 shared Simple LIVE source contract; not active in consumers  
**Canonical repository:** `rozkalnsandris/ops-workflows`  
**Tracking issue:** `#39`  
**Machine policy:** `policy/simple-live-v1.json`  
**Ready schema:** `policy/schemas/simple-live-ready-v1.schema.json`

## 1. Purpose

Simple LIVE v1 defines the single final owner decision used after a future adopted AUTO-RUN FULL Queue has completed all frozen source items and exact-main verification.

The target flow is:

```text
QUEUE_SOURCE_COMPLETE
-> final exact main + exact-main CI
-> full baseline-to-target classification
-> all obtainable GET/SELECT/read-only preflight
-> no live mutation required: DONE
   or
-> fixed reviewed consumer operation is READY
-> display one exact Simple LIVE ready envelope + binding digest
-> owner: LIVE <binding_sha256>
-> fresh same-envelope revalidation
-> one-shot fixed consumer rollout
-> public-safe final receipt
```

Simple LIVE is intentionally not a generic deployment transaction engine. The detailed mutation sequence lives in reviewed consumer source under one fixed operation identity.

A5 is source-policy-only. It does not activate Queue mode, create production authority, create a LIVE-AUTH issue, deploy anything, change credentials/permissions, mutate Cloudflare/D1, or mutate an RPi5 host/runtime.

## 2. Queue authority and LIVE authority remain separate

The Queue activation defined by A3 may eventually grant source + merge authority for its exact frozen issue set after explicit consumer adoption.

It never grants LIVE.

`QUEUE_SOURCE_COMPLETE` means only that all frozen source items have completed their exact source lifecycle. Before asking for LIVE, the controller must freshly reconstruct the final source and target facts.

A merge, `START`, `turpini`, event wakeup, watchdog tick, Queue receipt, Ready envelope, historical command or chat context is never LIVE authority.

## 3. Final read-only reconciliation

Before a Simple LIVE decision, the controller must obtain all evidence available without mutation, including as applicable:

- exact current consumer `main` SHA;
- required exact-main CI/checks;
- proven Queue completion chain;
- applicable consumer rules/trust boundary;
- full production-baseline -> final target deploy classification;
- exact target/environment/device alias;
- current production/runtime baseline when exposed;
- reviewed fixed operation ID and operation-contract identity;
- pinned/shared policy identity;
- public-safe preflight evidence;
- allowed mutation classes and hard mutation ceiling from the reviewed operation contract;
- explicit exclusions.

If the final classification is `NO_LIVE_REQUIRED`, finish without asking the owner for LIVE.

Unknown, ambiguous or incomplete classification is `BLOCKED`, not permission to guess.

## 4. Ready envelope is evidence, not authority

When owner LIVE is required, construct exactly one payload conforming to:

`policy/schemas/simple-live-ready-v1.schema.json`

Schema identity:

```text
rozkalns.simple-live-ready.v1
```

The envelope binds:

- Queue ID;
- exact source repository and final exact source SHA;
- exact target alias;
- fixed reviewed operation ID;
- SHA-256 digest of the reviewed operation contract;
- consumer-rules digest;
- immutable accepted `ops-workflows` shared-contract SHA;
- expected baseline, or an explicit reason when the platform cannot expose one;
- read-only preflight digest;
- allowed mutation classes;
- maximum total mutation count;
- explicit exclusions.

It contains no arbitrary shell command, argv, environment variables, dynamic operation graph or user-invented mutation sequence.

The Ready envelope is eligibility evidence only. It cannot execute anything by itself.

## 5. Binding digest and owner command

Canonicalize the complete Ready envelope as UTF-8 JSON with sorted keys and compact separators, then calculate SHA-256.

The resulting 64-character lowercase digest is `binding_sha256`.

The owner decision form is:

```text
LIVE <binding_sha256>
```

Before asking for that decision, show the owner the exact source SHA, target, operation ID, baseline, allowed mutation classes/ceiling, exclusions and binding digest in a concise Ready receipt.

A bare `LIVE` without the current binding digest is invalid under Simple LIVE v1.

The command is valid only for the exact Ready envelope that produced that digest. It does not mean “deploy latest main”.

## 6. Immediate pre-mutation revalidation

After the owner supplies the exact `LIVE <binding_sha256>` decision and before the first mutation, the controller must freshly re-read all authoritative facts needed to rebuild the Ready envelope.

Execution may begin only when:

```text
approved_binding
== binding_sha256(displayed_ready_envelope)
== binding_sha256(freshly_rebuilt_ready_envelope)
```

If `main`, target, operation identity, rules, baseline, preflight result, mutation classes/ceiling or exclusions changed, STOP and require a new owner decision.

Never reinterpret an older approval to mean a newer source SHA or changed target.

## 7. Fixed reviewed operation identity

The owner approves one fixed operation identity, not an arbitrary command list.

The consumer repository owns the operation contract and rollout adapter. That reviewed contract defines the deterministic technical sequence, mutation classes, hard ceilings, verification, postconditions and any explicitly permitted rollback/retry behavior.

`ops-workflows` may define schemas, policy and reusable GitHub-side guards. It does not store production credentials and does not become the production executor.

Repository-local stricter policy always wins.

## 8. One-shot execution and target serialization

After a valid owner decision, the trusted consumer execution plane should perform one fail-closed invocation that includes, as applicable:

```text
fresh read-only preflight
-> final SHA/target/baseline/binding revalidation
-> acquire stable target concurrency ownership
-> deterministic build/candidate preparation
-> capture exact immutable candidate identity
-> verify exact candidate identity
-> re-read target baseline/drift guard
-> perform only the fixed reviewed bounded rollout
-> read-only postconditions/reconciliation
-> emit one final receipt
```

At most one mutation-capable rollout may own a target at a time.

Concurrency prevents simultaneous writers; it does not replace baseline revalidation.

## 9. Authorization consumption and failure semantics

The Simple LIVE authorization is consumed when the first state-changing operation starts.

Before that point, failed read-only checks leave production unchanged and the controller remains fail-closed.

After mutation starts, any command error, ambiguous result, SHA/target/baseline drift, new mutation class, new trust-boundary condition or inability to prove state means:

```text
preserve public-safe evidence
-> STOP
```

Default behavior is no automatic:

- retry;
- rollback;
- cleanup;
- alternate mutation path;
- reset/rebase/force/history rewrite;
- unlisted follow-up mutation.

A fixed consumer operation may permit a bounded rollback/retry only when that behavior was explicitly reviewed, represented in the operation contract, compatible with the approved envelope, and proven safe before the first mutation.

## 10. Cloudflare Worker alignment

For a Cloudflare Worker operation, prefer version/deployment separation when the consumer adapter supports it:

```text
exact source SHA
-> deterministic build
-> upload/create one exact Worker version
-> capture VERSION_ID
-> verify that exact VERSION_ID candidate
-> revalidate production deployment baseline
-> deploy/promote that same verified VERSION_ID
```

Do not rebuild between candidate verification and production promotion when an immutable version identity exists.

Gradual/canary rollout is not the shared default. A consumer may require it only through its own reviewed risk contract.

Worker code/version rollback is not rollback of D1/KV/R2/Durable Object or other external mutable state. Simple LIVE therefore never treats code rollback as a generic full-system rollback.

D1 or other storage mutation is not implicitly included by a Worker rollout operation.

## 11. Deferred RPi5 execution keeps LIVE-AUTH v1

Simple LIVE does not replace the existing owner-authorized deferred RPi5 protocol in `docs/LIVE_AUTH_V1.md`.

For a direct same-session trusted consumer executor, a valid Simple LIVE decision may authorize the exact fixed operation when that direct execution path is already reviewed and enabled by the consumer.

For a deferred RPi5 pull executor, the owner decision must still be materialized through the existing LIVE-AUTH v1 contract before execution. The mapping from the Simple LIVE envelope to LIVE-AUTH must be lossless for source SHA, target, operation identity, baseline, allowed mutation budget/classes, exclusions and any other required LIVE-AUTH fields.

If that mapping cannot be proven, the deferred rollout is `BLOCKED`.

Simple LIVE does not change LIVE-AUTH owner identity, GitHub authorization-surface rules, TTL, replay prevention, consumption semantics, parser/transport boundary or trusted RPi5 operation registry.

A LIVE-AUTH object must never be created from bare `turpini`, Queue completion or Ready evidence before the current explicit owner LIVE decision.

## 12. Auto-Live v1 compatibility

A5 does not disable or silently replace existing Auto-Live v1 consumers.

For future Queue adoption, owner-driven Simple LIVE is the default final live mode. A consumer adoption must explicitly select one final live mode for each operation and prove that only one execution path can own that same operation/target.

Existing Auto-Live primitives such as exact-SHA checks, full-range classification, static operation identity, target serialization, health/postconditions and fail-closed behavior may be reused.

Do not create a double-execution path where both Auto-Live and Simple LIVE may independently mutate the same target for the same source transition.

## 13. Compatibility and migration boundary

Until a consumer explicitly adopts a completed Queue + Simple LIVE contract pinned to an immutable `ops-workflows` commit SHA:

- existing repository-local AUTO-RUN FULL remains authoritative;
- existing merge gates remain unchanged;
- Queue batch authority is not active;
- Simple LIVE is not an active command;
- Auto-Live v1 remains unchanged where already adopted;
- `GITHUB-ONLY / LIVE-ALL` compatibility artifacts remain available;
- no consumer is migrated by inference.

Shared policy merge alone changes no production/runtime behavior.

## 14. Shared / consumer / RPi5 responsibility boundary

### `ops-workflows`

Owns:

- Simple LIVE normative policy;
- machine-readable invariants;
- public-safe Ready-envelope schema;
- deterministic source validation;
- reusable GitHub-side guards in later slices;
- migration/compatibility rules.

Does not own:

- production credentials or private keys;
- consumer-specific deploy implementation;
- database apply logic;
- privileged RPi5 helpers;
- arbitrary remote shell/SSH command transport;
- generic production orchestration.

### Consumer repository

Owns:

- explicit adoption pinned to an immutable accepted shared SHA;
- deploy classification;
- fixed operation ID and reviewed adapter;
- exact operation-contract identity;
- target/environment mapping;
- least-privilege credentials;
- mutation classes/ceilings and exclusions;
- deterministic health/postconditions;
- local stricter rules.

### `RPi5_main`

Remains the trusted host/runtime execution boundary for RPi5-specific operations and owns the deferred LIVE-AUTH parser/executor/replay state.

## 15. A5 acceptance

A5 is complete when shared source/tests prove:

- Queue completion never itself grants LIVE;
- `NO_LIVE_REQUIRED` finishes without an owner gate;
- LIVE-required work has one fixed reviewed operation identity;
- Ready envelope binds exact SHA/target/baseline/rules/operation/preflight/mutation classes/ceiling/exclusions;
- owner command binds the Ready envelope by SHA-256 digest;
- bare LIVE and stale digest fail closed;
- fresh identical binding is required immediately before first mutation;
- authorization is consumed at first mutation and post-mutation errors STOP without undeclared retry/rollback/cleanup;
- target serialization and exact verified artifact principles remain intact;
- deferred RPi5 execution still requires existing LIVE-AUTH v1;
- Auto-Live and legacy compatibility are not silently changed;
- no consumer, production, credential, permission, Cloudflare/D1 or RPi5 mutation is activated by A5 itself.
