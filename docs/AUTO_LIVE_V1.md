# Auto-Live v1 — shared post-merge delivery contract

**Status:** A1 shared source policy — normal-operation target, compatibility migration phase
**Canonical repository:** `rozkalnsandris/ops-workflows`
**Machine contract:** `policy/auto-live-v1.json`
**Architecture authority for trusted RPi5 execution:** `rozkalnsandris/RPi5_main` issue #421 and repository-local source policy

## 1. Purpose

Auto-Live v1 replaces the normal operator-era `GITHUB-ONLY -> deferred LIVE-ALL` loop for production-bearing repositories after each consumer has explicitly migrated and activated its own reviewed manifest/adapter.

Target flow:

```text
reviewed PR -> merge -> exact merged SHA / exact-SHA CI -> trusted consumer controller
-> full baseline-to-target deploy classification -> safe automatic reconciliation -> health/evidence
```

This repository defines shared GitHub-side policy only. It is not a production execution environment and never carries RPi5 credentials, private keys, host mutation helpers, database apply logic, or arbitrary remote shell authority.

## 2. Merge is a trigger, not blanket live authority

A merge may make a new source SHA eligible for reconciliation. It does not itself authorize arbitrary production, root/sudo, systemd, Docker, networking, Cloudflare, credential, permission, database, destructive, or other sensitive mutation.

Automatic mutation is permitted only after the exact consumer repository/target/operation has completed its explicit Auto-Live activation and all repository-local gates still pass for the exact merged target.

## 3. Required consumer binding

No manifest means no automatic live mutation.

A production-bearing consumer must bind, in reviewed repository source:

- repository and stable production target alias;
- full production-baseline -> target deploy-impact classifier;
- exact required CI evidence for the merged SHA;
- static operation/capability identifier;
- classes eligible for automatic mutation;
- deterministic health/postconditions;
- declared retry/rollback behavior;
- explicit credential, permission, DB, host/control-plane, networking and destructive exclusions.

Consumers should pin accepted shared policy/workflow references to an immutable exact commit SHA. Mutable `main`, tags, and version branches are not production policy identities.

## 4. Classification

### `NO_DEPLOY`

Record/reconcile source state only. Production mutation is forbidden.

### `AUTO_DEPLOY_SAFE`

May automatically mutate only when the consumer has explicitly activated Auto-Live for that exact static operation and all exact-SHA, full-range, target, baseline, adapter-identity, concurrency and health gates pass.

### `MANUAL_ROLLOUT_REQUIRED`

Owner decision remains required. Merge does not narrow this class automatically.

### `DB_HOST_APPLY_REQUIRED`

Owner decision remains required. Database, host/control-plane, credential, permission and equivalent sensitive work is not promoted into automatic authority by this shared policy.

Unknown or ambiguous paths/classes fail closed.

## 5. Exact evidence and full-range classification

The controller must validate the complete proven production baseline -> intended target range, not only the newest commit. The target SHA must be the intended current merged source identity and required exact-SHA CI must be successful.

If source, target, baseline, policy, adapter identity, required CI or classification is ambiguous or drifts before mutation, the target is blocked without mutation.

## 6. Concurrency and supersession

Each production target has a stable concurrency key and at most one mutation-capable reconciliation may own that target at a time.

A newer merge may supersede an older still-pending target only before mutation starts and only after the complete production-baseline -> newer-target range is freshly reclassified.

## 7. Failure semantics

Pre-mutation read/transport failures may use only an explicitly reviewed bounded read retry policy.

Once the first production mutation starts, any error, ambiguity, source/baseline/target drift or authorization uncertainty preserves public-safe evidence and stops that target. No automatic retry, cleanup, rollback or alternate mutation path is implied. Such behavior is allowed only when the exact static operation contract predeclares it and its prerequisites were proven before mutation.

Independent targets may continue only when they share no dependency or target lock with the failed target.

## 8. Trusted execution boundary

Steady-state production reconciliation belongs in the consuming project's trusted runtime/controller plane. `ops-workflows` supplies reusable GitHub Actions and shared public-repository policy; it does not execute production mutations.

For the RPi5 architecture, Remote Desktop Commander is an owner-controlled bootstrap, recovery, convergence and maintenance transport only. It is not the steady-state merge detector, authorization store, generic privileged command bridge, or production source of truth.

This shared contract does not introduce an inbound public RPi5 webhook, a persistent self-hosted public-repository Actions deployment runner, PAT classic, generic SSH command transport, or arbitrary remote shell authority.

Prefer least-privilege GitHub App installation authentication with short-lived installation tokens where repository-local architecture requires GitHub reads.

## 9. `GITHUB-ONLY / LIVE-ALL` compatibility

`GITHUB-ONLY / LIVE-ALL v1` is superseded for normal operation by Auto-Live v1. Its documents, queue forms, LIVE-AUTH contract and historical issues remain available during controlled consumer migration and as audit history.

Compatibility mode must not be deleted while a current consumer still depends on it. A repository that has not completed its Auto-Live manifest/controller/canary migration continues to follow its existing stricter repository-local deployment contract.

Do not create new normal-operation dependence on the deferred queue when an in-scope consumer has completed Auto-Live activation for the same operation.

## 10. Source-only A1 boundary

A1 changes shared GitHub-side documentation, machine policy and CI validation only. It does not activate an RPi5 controller, enable an executor, change systemd/timers, modify credentials/App permissions, deploy an application, mutate a database/Cloudflare resource, or remove compatibility from live consumers.
