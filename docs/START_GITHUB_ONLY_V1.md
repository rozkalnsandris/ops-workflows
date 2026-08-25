# START GITHUB-ONLY v1 — deterministic bootstrap and parked-session semantics

**Status:** Accepted — canonical startup contract for `GITHUB-ONLY / LIVE-ALL v1`  
**Effective:** 2026-08-25  
**Issue:** #16  
**Canonical policy:** `docs/GITHUB_ONLY_LIVE_ALL.md`  
**Machine contract:** `policy/github-only-live-all-v1.json` (`schema_version: 2`)  
**Per-repository manifest:** `.github/start-github-only.json` validated by `policy/schemas/start-github-only-v1.schema.json`

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

On START, automation MUST perform these ten stages using fresh GitHub state:

1. resolve the canonical `owner/repository`, reject ambiguous aliases, record repository ID/default branch, and activate `GITHUB-ONLY`;
2. read repository-local `AGENTS.md`, path-scoped governing rules, and canonical master/handoff material, then declare the authority chain used;
3. read the shared `GITHUB-ONLY / LIVE-ALL` contract, this START contract, the machine policy, and the repository manifest; verify contract/schema/adoption compatibility before a source write;
4. snapshot the current default-branch identity and relevant governance capability;
5. inspect active PRs and normalize each candidate to current head/base, draft/mergeability, CI, review threads, risk, and explicit repository priority evidence;
6. inspect active issues, roadmap/handoff state, declared dependencies, and explicit priority evidence;
7. inspect relevant open `[DEPLOY-QUEUE]` items and classify rollout eligibility independently from current-session executor capability;
8. select the highest-priority canonical safe continuation using the manifest's total precedence and tie-break contract;
9. continue bounded GitHub/source work through Ready under repository-local gates and attempt limits, revalidating mutable target state immediately before every GitHub mutation that depends on it;
10. route the result to exactly one terminal/operator state: `READY_FOR_MERGE`, `PARKED`, `STOP_ERROR`, `NEW_SCOPE_OR_RISK`, `AMBIGUOUS_CANONICAL_LANE`, or `IDLE`.

The default continuation hierarchy is:

```text
explicit_current_handoff
> active_focused_pr_blocking_current_phase
> active_issue_declared_as_current
> deploy_queue_source_reconciliation
> explicitly_ordered_next_roadmap_item
> IDLE
```

A repository MAY override this hierarchy in `.github/start-github-only.json`, but the override must still be total and machine-resolvable.

Within one precedence class, use only repository-declared tie-break evidence, in this order by default:

1. explicit phase/priority;
2. explicit dependency order.

Do not infer priority from issue age, API return order, or issue/PR number unless the repository manifest explicitly declares such ordering. If two candidates remain equally authoritative, report `AMBIGUOUS_CANONICAL_LANE` and perform no arbitrary continuation write.

Candidates marked by machine-recognizable exclusion evidence such as `automation-fixture`, `do-not-merge`, `superseded`, or `parked-historical` are excluded from ordinary continuation unless governing repository evidence explicitly selects them.

`no open issue` by itself is **not** a STOP condition.

Do not invent speculative work merely to avoid an idle state. If no canonical safe continuation exists after the full bootstrap, report `IDLE`.

## 3. Snapshot versus just-in-time revalidation

The bootstrap snapshot selects the work lane; it does not freeze GitHub.

Before a GitHub mutation that depends on mutable state, automation MUST re-read the narrow state relevant to that mutation. Examples include the current default-branch SHA, PR head/base, mergeability, required CI, unresolved review threads, queue eligibility, and repository merge method.

A Ready receipt is invalidated by a changed candidate head until the new head is freshly validated. A merge authorization binds only the candidate described by the latest Ready receipt and remains subject to fresh pre-mutation validation.

## 4. START output UX

Avoid making the owner decode internal bootstrap mechanics. A normal START should briefly report the resolved mode and lane, then do the work.

Preferred compact form:

```text
<repo> | GITHUB-ONLY active | canonical state refreshed | continuing <lane>
```

Do not create owner actions for ordinary reads, CI polling, diff inspection, evidence refresh, queue inspection, capability probes, or other technical checkpoints.

## 5. Final-state router

The tenth bootstrap stage produces one of these states:

- `READY_FOR_MERGE` — exact PR is Ready; one explicit merge decision is required;
- `PARKED` — all safe GitHub/source work is complete and valid deferred live work is READY; no owner action is required now;
- `STOP_ERROR` — a source-level invariant or attempt limit prevents safe continuation;
- `NEW_SCOPE_OR_RISK` — the next action crosses a new trust/risk boundary and requires one exact owner decision;
- `AMBIGUOUS_CANONICAL_LANE` — repository evidence cannot deterministically resolve between equally authoritative lanes;
- `IDLE` — no canonical safe continuation exists and no speculative task is created.

`ACTION REQUIRED` is shown only for a real current owner decision.

## 6. PARKED session semantics

When all possible GitHub/source work is complete and a future live rollout is represented by a valid `[DEPLOY-QUEUE][READY]` issue, the GITHUB-ONLY session ends conceptually as:

```text
PARKED — deferred live work is READY.
NO ACTION REQUIRED NOW.
```

`PARKED` is a session/operator UX state only. It is **not** a deploy-queue issue title state and must not replace `[READY]`.

Do not pressure the owner to run `LIVE-ALL` immediately. `LIVE-ALL` is used later, from a session/environment that can satisfy the selected queue items' declared executor requirements.

## 7. Executor availability is not queue readiness

Queue readiness describes the rollout candidate and its declared contract. Session executor availability describes the current operator session's capabilities. They are different dimensions.

Therefore:

```text
READY + declared executor unavailable in this session
= queue remains READY
= session reports PARKED / EXECUTOR_UNAVAILABLE
= no live mutation occurs
```

Lack of a `trusted-home-host`, SSH channel, device bridge, or another declared executor in the current session must not by itself change a valid queue item from `[READY]` to `[BLOCKED]`.

Before starting a `LIVE-ALL` batch, automation MUST run only the declared non-mutating capability probe for each READY item's execution class. The probe answers only whether the current session can execute the already-declared envelope. It must not mutate a target, read protected runtime data, install packages, restart services, or widen trust.

If no READY item is executable, no live batch starts, no authorization is consumed, and the session remains `GITHUB-ONLY / PARKED`.

## 8. When BLOCKED is correct

`[BLOCKED]` is reserved for a problem with rollout eligibility or contract validity, such as:

- approved source SHA is no longer the intended deployable candidate;
- target identity or required baseline conflicts with the queue contract;
- required dependency is incomplete or failed;
- required CI/review/post-merge evidence no longer satisfies the contract;
- reviewed deployment entrypoint is missing or changed incompatibly;
- a newly required secret, permission, database, infrastructure, trust-boundary, or undeclared mutation category makes the ordinary envelope invalid;
- another candidate/target/policy drift makes the rollout itself ineligible.

Executor unavailability alone is not candidate, target, baseline, dependency, or policy drift. A BLOCKED transition must record a structured blocked reason plus public-safe evidence.

## 9. LIVE-ALL interaction

`LIVE-ALL` remains an explicit owner authorization for an executable frozen snapshot of ordinary READY items.

At command start:

1. read the canonical policy and all open queue items fresh;
2. identify READY items;
3. build and validate the dependency DAG and same-target conflict set;
4. perform read-only executor-capability checks for declared execution-location classes;
5. freeze only READY items that are dependency-valid, conflict-free, executable in the current session, and otherwise eligible;
6. leave READY-but-executor-unavailable items unchanged and report them as parked/not selected;
7. revalidate exact SHA/target/baseline/CI/entrypoint immediately before each selected item's first live mutation.

A dependency cycle causes a no-mutation stop. Two READY items targeting the same deployment without an explicit dependency/order relationship are not guessed into an order; they remain unselected pending queue reconciliation.

If no READY item is executable in the current session, perform no mutation, consume no live authorization, and report that the queue remains parked for a compatible executor session.

## 10. Owner-facing action rule

Show an `ACTION REQUIRED` section only when a genuine current owner decision remains.

Examples:

- exact merge authorization is required now;
- a new risk/scope decision is required now;
- an ambiguous canonical lane cannot be resolved from repository evidence.

Do not present `LIVE-ALL` as a mandatory next action merely because a READY queue item exists.
