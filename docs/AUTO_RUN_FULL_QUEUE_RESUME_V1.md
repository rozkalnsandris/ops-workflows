# AUTO-RUN FULL Queue resume/events/watchdog v1

**Status:** A4 shared resume source contract; not active in consumers  
**Canonical repository:** `rozkalnsandris/ops-workflows`  
**Tracking issue:** `#39`  
**Parent contracts:** `AUTO_RUN_FULL_QUEUE_V1.md`, `AUTO_RUN_FULL_QUEUE_CONTROLLER_V1.md`, `AUTO_RUN_FULL_QUEUE_AUTHORIZATION_V1.md`

## 1. Purpose

A4 defines how an already-authorized future Queue controller should wake up again after asynchronous GitHub activity without turning webhook payloads, scheduled jobs, runner queues or chat history into authority.

The core rule is:

```text
trigger wakes controller
-> controller freshly re-reads canonical GitHub state
-> existing A2/A3 contracts decide what may happen
```

A trigger is a notification, not a state transition and not an authorization.

A4 does not activate Queue mode in any consumer, create a webhook, create a scheduled task, grant source/merge authority, bypass an owner gate or authorize LIVE.

Existing repository-local AUTO-RUN FULL remains authoritative until explicit per-consumer adoption of a later completed Queue contract.

## 2. Resume sources

Initial target order:

1. **GitHub event-triggered task** — primary, near-real-time wakeup when the configured orchestration surface receives relevant GitHub activity.
2. **Scheduled watchdog** — fallback recovery path when the primary wakeup is missed, delayed or unavailable.
3. **Manual continuation** — `turpini` or equivalent may resume the same already-authorized Queue after fresh retrieval; it creates no new authority.

The intended current product mapping may use a ChatGPT Work GitHub-event-triggered task as the primary transport and a ChatGPT scheduled task as the watchdog, but A4 deliberately keeps the machine contract transport-independent. No product integration is activated by merging A4.

Reference watchdog cadence for v1 is **60 minutes**. It is a recovery interval, not an execution SLA.

## 3. Canonical-state rule

Neither an event payload nor a watchdog tick may be used directly to:

- advance the Queue cursor;
- change `active_issue`;
- mark an item `SOURCE_COMPLETE`;
- infer CI/review/merge success;
- grant source or merge authority;
- bypass an owner gate;
- grant LIVE;
- alter frozen issue order or scope.

After every wakeup, the controller must freshly retrieve the minimum canonical facts needed for the current lane, including as applicable:

- the unique current consumer Queue/controller issue and immutable A3 authorization receipt;
- current A2 controller state;
- the same ACTIVE issue and its frozen identity/scope digest;
- applicable repository rules/trust boundary;
- current `main` and the proven Queue main chain;
- current PR/head SHA;
- exact-head CI/checks;
- reviews and unresolved review threads;
- exact-main source-terminal evidence before any advance.

If those facts cannot be proven, fail closed.

## 4. Relevant GitHub wake events

The initial event-family allowlist is intentionally broad enough to avoid brittle dependence on one CI implementation but narrow enough to exclude unrelated repository noise:

```text
issues
issue_comment
pull_request
pull_request_review
pull_request_review_comment
check_suite
check_run
status
push
```

A consumer/event bridge may apply stricter action filters, for example only `pull_request.synchronize`, review submission, completed checks or default-branch push.

Unknown event families are ignored.

The event action itself never decides the Queue transition. A `check_run.completed` payload, for example, only causes the controller to wake and re-read exact canonical check state for the current PR/head.

## 5. Duplicate and out-of-order delivery

Resume must be idempotent.

When the transport exposes GitHub's delivery identifier, use it as a best-effort dedupe key. A redelivery of the same GitHub webhook retains the same delivery GUID, so this is useful for suppressing unnecessary duplicate work.

Dedupe is an optimization, not a safety dependency. Duplicate, delayed or out-of-order wakeups must remain safe because every wakeup reconstructs current state from GitHub before acting.

No event payload may widen the frozen A3 scope or authority.

## 6. Queue-state behavior after refresh

A wakeup may only produce these coarse dispositions:

### `READY`

```text
NO_AUTO_ACTIVATION
```

A signal does not activate a Queue. Activation still requires the explicit future Queue owner command and durable A3 receipt.

### `ACTIVE`

```text
RESUME_SAME_ACTIVE_ITEM_AFTER_REFRESH
```

Continue only after A2/A3/current repository gates pass.

### `PAUSED`

```text
RESUME_SAME_ACTIVE_ITEM_ONLY_IF_REFRESH_AND_AUTHORITY_PASS
```

The signal cannot change cursor or select a different item.

### `QUEUE_SOURCE_COMPLETE`

```text
READ_ONLY_FINAL_RECONCILIATION_ONLY
```

A4 may wake the final exact-main/read-only reconciliation path. It does not grant the later LIVE authority.

### `STOPPED`

```text
NO_AUTO_RESUME
```

An event, watchdog tick or manual continuation must not silently clear STOPPED. Fresh owner/source authorization is required according to the contract that caused the stop.

## 7. Owner-gate preservation

Event-driven continuation exists to remove polling friction, not decision gates.

A wakeup must not bypass:

- legacy explicit MERGE when the consumer has not adopted A3 Queue merge authority;
- any repository-local stricter merge/review rule;
- a required final owner LIVE decision;
- a STOP caused by scope/rules/risk/trust-boundary drift.

Queue resume is never LIVE authority.

## 8. Watchdog behavior

The watchdog exists only to recover continuation when no useful primary event was processed.

On each tick it should:

1. identify the configured consumer repository/controller;
2. retrieve only the minimum current canonical state;
3. determine whether the current Queue has safe continuation work;
4. do nothing when there is no actionable continuation;
5. preserve STOPPED and owner-gated states;
6. never add/reorder/skip Queue items;
7. never create source/merge/LIVE authority.

A primary event and watchdog tick may arrive close together. This must be harmless and idempotent.

## 9. GitHub webhook transport security

If a future implementation uses a GitHub webhook transport directly, transport security is owned by that receiving integration, not by `ops-workflows` source policy.

The receiver should follow GitHub's webhook guidance, including validating the webhook signature using a securely stored secret and using the delivery identifier for replay/dedup handling where available.

`ops-workflows` must not store the webhook secret or become the public webhook execution server.

GitHub does not automatically redeliver failed webhook deliveries. A4 therefore treats the independent watchdog as the normal recovery path for missed wakeups rather than requiring a privileged webhook-redelivery mechanism.

## 10. Scheduled-trigger limitations

A watchdog must not be treated as precise scheduling or as canonical progress state.

GitHub documents that scheduled Actions can be delayed under high load and in sufficiently high load conditions queued scheduled jobs can be dropped. This reinforces the A4 rule that a schedule is only a fallback wake source, never an authority or timing SLA.

The same design applies when the watchdog is implemented outside GitHub Actions: it only requests a fresh canonical refresh.

## 11. `workflow_run` privilege boundary

A4 does not require a privileged GitHub Actions `workflow_run` executor.

GitHub documents that `workflow_run` can run with access to secrets and write tokens even when the triggering workflow did not have them. A future implementation must not use that property to turn untrusted CI output/artifacts into Queue authority or broaden permissions.

Preferred design remains:

```text
GitHub event -> low-authority wake signal -> fresh GitHub reads -> existing reviewed controller authority
```

Any future Actions-based event adapter must use least privilege and remain only a wake/validation surface unless separately reviewed.

## 12. Resume signal schema

Shared source schema:

`policy/schemas/auto-run-full-queue-resume-signal-v1.schema.json`

Schema identity:

```text
rozkalns.auto-run-full-queue-resume-signal.v1
```

The signal contains only routing metadata such as repository identity, source/event identity, optional delivery ID, observation time and optional issue/PR hints.

It intentionally contains **no authority flags, no source scope, no cursor, no merge permission and no LIVE permission**.

Hints may reduce retrieval cost but never replace canonical lookup.

## 13. Shared validator

`scripts/validate_auto_run_full_queue_resume.py` validates signal shape and exposes pure helpers for:

- event-family filtering;
- repository identity filtering;
- delivery-ID dedupe key generation;
- safe disposition after the caller has completed canonical refresh/revalidation.

The helper deliberately cannot advance the A2 cursor or create A3 authority.

## 14. Compatibility boundary

A4 preserves all earlier migration boundaries:

- no Queue command is active in any consumer because of A4;
- no event/task/watchdog is created automatically;
- old AUTO-RUN FULL remains authoritative until explicit adoption;
- A3 batch authority is dormant until a consumer adopts it;
- no consumer is auto-migrated;
- no production credentials or webhook secrets move into `ops-workflows`;
- `RPi5_main` remains the trusted host/runtime boundary;
- LIVE remains separately owner-authorized.

## 15. A4 acceptance

A4 is complete when shared source/tests prove:

- event/watchdog/manual wakeups are notifications only;
- GitHub is freshly re-read before action;
- duplicate/out-of-order signals are safe;
- event payload cannot advance Queue state;
- READY cannot auto-activate;
- STOPPED cannot auto-resume;
- owner gates remain intact;
- Queue source completion only opens read-only final reconciliation;
- watchdog is fallback and not an SLA;
- no consumer/runtime integration is activated by A4 itself.
