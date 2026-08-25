# START GITHUB-ONLY v1 — deterministic bootstrap and parked-session semantics

**Status:** Proposed clarification to accepted `GITHUB-ONLY / LIVE-ALL v1`  
**Issue:** #16  
**Canonical policy:** `docs/GITHUB_ONLY_LIVE_ALL.md`  
**Machine contract:** `policy/github-only-live-all-v1.json`

This document standardizes the operator UX for commands shaped like:

```text
START <repository> GITHUB-ONLY
```

It does not weaken repository-local rules, merge gates, live-mutation gates, or `LIVE-ALL` revalidation requirements.

## 1. Core rule

`START <repository> GITHUB-ONLY` means:

> Refresh canonical GitHub state, deterministically find the next safe canonical work lane, and continue GitHub/source work through the normal Ready/STOP boundary without asking the owner to infer routine technical next steps.

A START session is not merely a status report and must not mechanically require an open issue when another canonical continuation source exists.

## 2. Deterministic bootstrap order

On START, automation should perform this order using fresh GitHub state:

1. resolve the exact repository and activate `GITHUB-ONLY`;
2. read repository-local `AGENTS.md` / governing rules and canonical master/handoff material;
3. read the shared `GITHUB-ONLY / LIVE-ALL` contract and this START contract;
4. read current default branch / `main` identity;
5. inspect active PRs and their Ready/CI/review state;
6. inspect active issues, master roadmap/handoff state, and declared dependencies;
7. inspect relevant open `[DEPLOY-QUEUE]` items in `rozkalnsandris/ops-workflows`;
8. select the highest-priority canonical safe continuation that is supported by repository evidence;
9. continue source/GitHub work through Ready, subject to repository-local gates and attempt limits.

Canonical continuation sources may include, in repository-defined precedence:

- an explicit current handoff or master issue;
- an active focused PR needing source-level completion, CI/review, or bounded correction;
- an active implementation issue;
- a deferred deploy queue dependency that requires GitHub/source reconciliation;
- the next bounded roadmap item when the repository explicitly defines deterministic issue ordering and enough evidence exists to create it.

`no open issue` by itself is **not** a STOP condition.

Do not invent speculative work merely to avoid an idle state. If no canonical safe continuation exists after the full bootstrap, report `IDLE`.

## 3. START output UX

Avoid making the owner decode internal bootstrap mechanics. A normal START should briefly report the resolved mode and lane, then do the work.

Preferred compact form:

```text
<repo> | GITHUB-ONLY active | canonical state refreshed | continuing <lane>
```

Do not create owner actions for ordinary reads, CI polling, diff inspection, evidence refresh, queue inspection, or other technical checkpoints.

## 4. Normal STOP states

A GITHUB-ONLY session should stop only when a real owner decision or safety boundary remains, for example:

- `READY_FOR_MERGE` — exact PR is Ready and merge requires explicit owner authorization;
- `STOP_ERROR` / attempt-limit stop — source-level work cannot safely continue under the current authorization;
- `NEW_SCOPE_OR_RISK` — the next action crosses a new trust boundary or risk class;
- `IDLE` — no canonical safe continuation exists.

A deferred ordinary live rollout that is fully prepared is **not** an immediate owner-action stop in the current GITHUB-ONLY session.

## 5. PARKED session semantics

When all possible GitHub/source work is complete and a future live rollout is represented by a valid `[DEPLOY-QUEUE][READY]` issue, the GITHUB-ONLY session ends conceptually as:

```text
PARKED — deferred live work is READY.
NO ACTION REQUIRED NOW.
```

`PARKED` is a session/operator UX state only. It is **not** a deploy-queue issue title state and must not replace `[READY]`.

Do not pressure the owner to run `LIVE-ALL` immediately. `LIVE-ALL` is used later, from a session/environment that can satisfy the selected queue items' declared executor requirements.

## 6. Executor availability is not queue readiness

Queue readiness describes the rollout candidate and its declared contract. Session executor availability describes the current operator session's capabilities. They are different dimensions.

Therefore:

```text
READY + declared executor unavailable in this session
= queue remains READY
= session reports PARKED / EXECUTOR_UNAVAILABLE
= no live mutation occurs
```

Lack of a `trusted-home-host`, SSH channel, device bridge, or another declared executor in the current session must not by itself change a valid queue item from `[READY]` to `[BLOCKED]`.

Before starting a `LIVE-ALL` batch, automation should determine whether the current session can access each READY item's declared execution-location class. Items whose executor is unavailable in the current session are not executable in that session and remain READY for a future compatible session. This capability check is read-only and consumes no live authorization.

## 7. When BLOCKED is correct

`[BLOCKED]` is reserved for a problem with rollout eligibility or contract validity, such as:

- approved source SHA is no longer the intended deployable candidate;
- target identity or required baseline conflicts with the queue contract;
- required dependency is incomplete or failed;
- required CI/review/post-merge evidence no longer satisfies the contract;
- reviewed deployment entrypoint is missing or changed incompatibly;
- a newly required secret, permission, database, infrastructure, trust-boundary, or undeclared mutation category makes the ordinary envelope invalid;
- another candidate/target/policy drift makes the rollout itself ineligible.

Executor unavailability alone is not candidate, target, baseline, dependency, or policy drift.

## 8. LIVE-ALL interaction

`LIVE-ALL` remains an explicit owner authorization for an executable frozen snapshot of ordinary READY items.

At command start:

1. read the canonical policy and all open queue items fresh;
2. identify READY items;
3. perform a read-only executor-capability check for their declared execution-location classes;
4. freeze only the READY items that are executable in the current session and otherwise eligible;
5. leave READY-but-executor-unavailable items unchanged and report them as parked/not selected;
6. proceed with normal exact SHA/target/baseline revalidation before each selected item's first live mutation.

If no READY item is executable in the current session, perform no mutation, consume no live authorization, and report that the queue remains parked for a compatible executor session.

## 9. Owner-facing action rule

Show an `ACTION REQUIRED` section only when a genuine current owner decision remains.

Examples:

- exact merge authorization is required now;
- a new risk/scope decision is required now;
- the owner explicitly wants to execute live work and must move to a compatible execution session.

Do not present `LIVE-ALL` as a mandatory next action merely because a READY queue item exists.
