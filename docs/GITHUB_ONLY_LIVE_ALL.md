# GITHUB-ONLY / LIVE-ALL v1 — deferred deployment queue

**Status:** Accepted  
**Decision date:** 2026-08-25  
**Canonical repository:** `rozkalnsandris/ops-workflows`  
**Machine contract:** `policy/github-only-live-all-v1.json`  
**Deferred pull authorization:** `docs/LIVE_AUTH_V1.md` / `policy/live-auth-v1.json`

This policy adds an operator mode on top of FAST-LANE v2.2 Composite. Repository-local stricter trust-boundary rules always win.

## 1. Purpose

The operator needs a safe mode for working away from the production environment:

- do all possible GitHub/source work now;
- prepare every required live/deploy operation up to the first live mutation;
- persist the exact deferred rollout in GitHub instead of chat or memory;
- later, from the trusted home environment, execute the prepared ordinary deployment queue with one explicit owner decision.

GitHub is the canonical continuation store. Chat history and assistant memory are never sufficient deployment state.

## 2. Commands

### `GITHUB-ONLY`

`GITHUB-ONLY` (including the human spelling `git hub only`) activates deferred-live mode.

While active, automation may perform only GitHub/source-level work and read-only external evidence needed to prepare a rollout. It may:

- refresh repository rules, current `main`, issue/PR state, CI/review state and relevant documentation;
- create/update issues, focused branches, commits, Draft PRs and source documentation;
- run or inspect source validation and GitHub CI/review;
- use the normal FAST envelope through Ready, including scope-preserving corrections allowed by the governing repository;
- after a separately authorized merge, refresh exact post-merge GitHub evidence and prepare the exact rollout candidate;
- create/update a deferred deployment queue issue in this repository.

It must not perform the first production/live mutation. In particular it must not:

- deploy or publish to production;
- mutate a production host, container, service, scheduler, device or runtime;
- perform production database writes/migrations;
- mutate Cloudflare DNS/Tunnel/Access or equivalent infrastructure configuration;
- change secrets, credentials, permissions or trust boundaries;
- perform destructive cleanup;
- perform a GitHub action whose deterministic side effect is an otherwise forbidden production/live mutation.

`GITHUB-ONLY` never authorizes merge. Merge remains a separate explicit owner decision under the repository's normal merge gate.

`GITHUB-ONLY` also never authorizes creation of a LIVE-AUTH object for an active deferred pull executor. Once such an executor exists, creating LIVE-AUTH can deterministically lead to a later production mutation and therefore belongs to an explicit current live/deploy decision, not source preparation.

The mode stays active until `LIVE-ALL` completes/stops or the owner explicitly cancels the mode.

### `LIVE-ALL`

`LIVE-ALL` is an explicit owner authorization decision for the snapshot of ordinary deployment queue items that are `READY` at command time, subject to every rule below.

It is not merge authorization and does not authorize separately gated high-risk categories.

For a direct same-session executor, the frozen LIVE-ALL snapshot may be executed under the existing bounded one-shot contract. For a deferred RPi5 pull executor that will execute later, the selected owner decision must additionally be materialized as one short-lived owner-authored LIVE-AUTH issue per selected queue item under `docs/LIVE_AUTH_V1.md`. The later pull executor accepts that GitHub authorization object, not raw chat context.

## 3. Queue transport and identity

The canonical queue is GitHub Issues in `rozkalnsandris/ops-workflows`.

Queue issue title states are:

- `[DEPLOY-QUEUE][WAITING]` — source/merge/dependency is not yet ready;
- `[DEPLOY-QUEUE][READY]` — eligible for a future live decision;
- `[DEPLOY-QUEUE][BLOCKED]` — read-only revalidation failed before live mutation;
- `[DEPLOY-QUEUE][EXECUTING]` — selected in an active execution and execution started;
- `[DEPLOY-QUEUE][STOP_ERROR]` — a mutation started and execution stopped on error/ambiguity;
- closed issue — successfully reconciled `DONE`, or explicitly cancelled with a recorded reason.

**READY is eligibility only. It is never execution authorization by itself.** In particular, an asynchronous/deferred pull executor must not execute merely because it observes a READY queue item.

One queue issue represents one coherent rollout to one exact target. Do not combine unrelated targets or independent risk classes in one queue item.

## 4. Required queue fields

Every queue item must contain public-safe values for:

- source repository;
- exact immutable 40-character Git SHA to deploy, or `WAITING_MERGE` until the final merged SHA exists;
- source PR/issue when applicable;
- exact target/environment/device alias;
- execution location class, such as `github-actions`, `trusted-home-host`, or another repository-defined trusted executor;
- exact repository workflow/script/controller entrypoint;
- expected pre-mutation baseline/version/SHA when the target exposes one;
- read-only preflight steps/evidence;
- post-deploy verification/reconciliation steps;
- allowed mutation categories and practical operation limits;
- explicit exclusions;
- dependency queue issue(s), if any;
- deploy classification and whether another owner gate is required.

Never put secrets, tokens, passwords, private keys, authenticated cookies/storage, service credentials, protected configuration, or unredacted sensitive logs in a queue issue.

Because `ops-workflows` is public, private absolute host details should not be added merely for convenience. Store a stable trusted execution alias plus the exact reviewed repository entrypoint; resolve private local checkout details read-only at live time when required by the project contract.

## 5. Queue creation under `GITHUB-ONLY`

When a source change is known to require a future rollout but is not yet merged, create or update one queue issue as `WAITING` and bind it to the exact PR/head evidence available.

After an explicit merge:

1. re-read current `main` and exact merge result;
2. classify deploy/live impact under the project contract;
3. if no rollout is required, close/cancel any stale queue item with evidence;
4. if rollout is required, replace provisional head identity with the exact merged/current deployable SHA;
5. collect all obtainable read-only target/baseline evidence;
6. prepare the exact workflow/script/controller and verification path;
7. mark the queue item `READY` only when no additional source work or separate prerequisite owner gate is outstanding.

Do not mark an item `READY` merely because a PR is Ready for merge. Do not create LIVE-AUTH as part of this source-preparation step.

## 6. `LIVE-ALL` snapshot semantics

At the start of `LIVE-ALL`:

1. freshly read this canonical policy and all open `[DEPLOY-QUEUE]` issues;
2. perform the read-only executor-capability check;
3. select only items whose current title/state is `READY` and executable in the current session/declared executor class;
4. freeze the selected issue numbers and their exact declared repo/SHA/target/mutation envelope as the batch snapshot;
5. do not automatically include queue items created or promoted to `READY` after the snapshot;
6. resolve declared dependencies and execute sequentially by default;
7. never execute two rollouts concurrently against the same target.

A queue item that requires merge, DB writes/migrations, secret/credential changes, permission/trust-boundary expansion, destructive cleanup, DNS/Tunnel/Access changes, or another separately gated risk is not an ordinary `LIVE-ALL` item. Leave it `WAITING`/`BLOCKED` with the exact required owner decision.

READY items that cannot be executed in the current session remain READY. Executor unavailability alone is not BLOCKED.

## 7. Deferred pull authorization materialization

For an ordinary READY item selected for the deferred RPi5 pull executor:

1. finish all obtainable read-only queue/source/CI/target/baseline revalidation before creating authorization;
2. require a current explicit owner live/deploy decision (`LIVE-ALL` for the frozen ordinary batch or an exact repository-local deployment command);
3. create exactly one `[LIVE-AUTH][PENDING] <target_alias>` Issue for exactly one selected queue item using the frozen values;
4. bind exact source repository/SHA, target, `operation_id`, expected baseline, mutation budget, rollback policy, exclusions and dependencies;
5. use the fixed 600-second TTL defined by `policy/live-auth-v1.json`; comments, labels, edits, reactions or locks never extend it;
6. do not create LIVE-AUTH if the executor is unavailable or is unlikely to discover and revalidate the request inside the TTL; leave the queue item READY instead;
7. the pull executor must independently re-fetch and validate the GitHub Issue, owner numeric identity, authorization-surface governance, queue state, source/CI/baseline, body hashes and local replay state immediately before its mutation-capable boundary.

`START`, `turpini`, PR Ready, merge, `GITHUB-ONLY`, queue READY, a previous `LIVE-ALL`, a historical authorization, a receipt, or executor availability never imply a new LIVE-AUTH.

The autonomous authorization reader must be read-only on the LIVE-AUTH surface. Result reporting is a separate non-authority capability and must not grant the authorization reader issue-write authority.

## 8. Ordinary live mutations that `LIVE-ALL` may cover

Only when explicitly declared in a `READY` queue item and allowed by the repository-local contract, `LIVE-ALL` may cover tightly bounded ordinary rollout operations such as:

- trusted checkout `git fetch` and `git merge --ff-only` when required and predeclared;
- deterministic application build/release preparation using repository-pinned tooling;
- upload/create of the exact approved immutable application artifact/version;
- bounded application/Worker deployment or promotion of that exact verified candidate;
- the minimum service/container restart that is an already-reviewed part of that exact application deployment;
- read-only candidate smoke verification and post-deploy reconciliation;
- GitHub queue status/evidence updates through an independently authorized/reporting-capable path.

It does not permit `reset`, `rebase`, `clean`, force/history rewrite, ad-hoc package repair, unlisted restarts, unlisted host changes or an alternate deploy path.

## 9. Fresh revalidation before each rollout

Before the first live mutation of every selected queue item, revalidate at least:

- queue issue is still open and still in the frozen snapshot;
- for deferred pull execution, LIVE-AUTH is valid, unexpired, unchanged and unconsumed;
- repository/local contract still allows the declared operation;
- exact approved SHA is still the intended deployable source identity;
- required CI/review/post-merge evidence still passes;
- exact target still matches;
- expected production/runtime baseline still matches when observable;
- dependencies completed successfully;
- execution entrypoint/operation identity is still the reviewed exact contract;
- no new permission, secret, database, infrastructure or trust-boundary mutation is required.

Any drift before mutation means fail closed for that item. Mark it `BLOCKED` with public-safe evidence when a reporting path is separately authorized. Independent later items may continue only when no dependency/target relationship is affected and no live mutation for the failed item started.

## 10. Mutation start and failure rule

For direct same-session `LIVE-ALL`, the batch authorization is consumed when the first authorized state-changing operation of the batch starts.

For deferred pull execution, each LIVE-AUTH request is locally marked consumed before crossing the mutation-capable adapter boundary; a consumed request can never execute again.

After any selected item's live mutation starts, an error, ambiguous result, unexpected drift, inability to prove target identity, or newly required mutation category requires:

`preserve public-safe evidence -> STOP_ERROR -> STOP the remaining dependent/authorized execution according to the frozen contract`

Do not automatically retry, rollback, clean up, reset/rebase, select an alternate target/path, or continue to later dependent items unless that exact behavior was explicitly pre-authorized in the frozen envelope and allowed by the repository-local contract.

## 11. Completion and receipts

For each successful item:

1. run the declared read-only reconciliation;
2. require the observed deployed/runtime identity to match the exact approved candidate where the platform exposes identity;
3. produce a concise public-safe receipt using `rozkalns.deploy-receipt.v1` where the executor path supports it;
4. record before/after target identity and actual mutation counts;
5. close/reconcile the queue issue only through a separately reviewed reporting-capable path.

A receipt is evidence only. It never authorizes execution, extends TTL, reopens a consumed request, or causes an automatic retry. Reporting failure must never repeat a deployment merely to repair GitHub status.

At batch end, report:

- frozen queue issue numbers;
- completed items;
- blocked/not-run items;
- whether the first mutation started and authorization was consumed;
- exact production/runtime changes performed;
- the next owner decision only when one genuinely remains.

## 12. Relationship to FAST-LANE v2.2

FAST-LANE remains the risk/decision framework:

`source work -> explicit MERGE -> post-merge read-only evidence -> live decision -> one-shot execution`

`GITHUB-ONLY` changes *when* the live decision is taken by persisting the prepared rollout instead of requesting it immediately.

`LIVE-ALL` is a batch Composite Live owner decision only for the frozen set of ordinary `READY` queue items. A direct executor may consume that decision in-session. A deferred pull executor additionally requires the exact short-lived GitHub LIVE-AUTH materialization defined above. Neither path weakens repository-local stricter gates.
