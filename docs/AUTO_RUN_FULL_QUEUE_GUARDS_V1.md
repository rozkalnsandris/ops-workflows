# AUTO-RUN FULL Queue reusable guards v1 — A6

**Status:** shared source-policy / CI guard design, not active in any consumer.  
**Tracking:** `ops-workflows#39`.  
**Production execution:** none.

## Purpose

A1 through A5 intentionally introduced separate contracts for Queue shape, deterministic controller state, batch source+merge authorization, resume semantics and Simple LIVE. A6 adds the composition layer that must fail closed when those contracts drift apart and provides one reusable read-only CI guard for future consumer adoption.

A6 does **not** activate `AUTO-RUN FULL QUEUE` in any repository. A shared-policy merge does not migrate a consumer, create Queue authority, create LIVE authority, change repository settings, or install an executor.

## Shared composition guard

`policy/auto-run-full-queue-guards-v1.json` and `scripts/validate_auto_run_full_queue_guards.py` compose the accepted A1-A5 invariants with the existing Auto-Live v1 boundary.

The composition guard requires at least these properties:

- the shared Queue command remains inactive in `ops-workflows`;
- future adopted Queue mode is bounded to 1-10 explicit ordered issues;
- at most one issue is ACTIVE;
- A3 may grant source + merge authority for all frozen issues only after an explicit per-consumer adoption and exact Queue activation;
- Queue authority never includes LIVE;
- event/watchdog/manual wake signals never become authority and never advance the cursor directly;
- a Simple LIVE Ready envelope is evidence, not authority;
- owner LIVE is separately explicit when Simple LIVE is selected;
- merge never authorizes LIVE;
- `ops-workflows` never executes production and never stores production credentials;
- deferred RPi5 execution preserves the existing LIVE-AUTH v1 trust boundary;
- one operation must not have parallel Simple LIVE and Auto-Live execution paths.

A pinned shared revision that violates any composed invariant is not an acceptable consumer contract.

## Consumer adoption manifest

Future adopters use a repository-local manifest, default path:

`.github/auto-run-full-queue-adoption-v1.json`

Schema:

`policy/schemas/auto-run-full-queue-adoption-v1.schema.json`

The manifest is intentionally small. It records only the migration phase and the shared trust-boundary assertions needed to prove that the consumer is adopting the same Queue semantics. It is not a deployment operation registry and must not contain credentials or protected runtime data.

### Required identity binding

The manifest binds:

- exact caller repository;
- exact immutable 40-character lowercase `ops-workflows` commit SHA;
- one adoption phase;
- Queue authority limits;
- one final-live mode;
- shared/consumer execution boundaries.

The consumer CI workflow must call:

`rozkalnsandris/ops-workflows/.github/workflows/auto-run-full-queue-adoption-guard.yml@<exact-40-char-sha>`

Every caller workflow reference to this guard must use the same exact SHA recorded by the manifest. Mutable `main`, tags or version branches are rejected.

## Adoption phases

### `SOURCE_ONLY_CANARY`

This is the first consumer migration state.

Required behavior:

- Queue command may be explicitly activated under the adopted repository contract;
- frozen batch source authority = enabled;
- frozen batch merge authority = enabled;
- Queue LIVE authority = disabled;
- final-live mode = `DISABLED`;
- existing production/runtime behavior must not be silently changed by this phase.

The source-only canary proves Queue ordering, scope freeze, one-ACTIVE behavior, PR/CI/review convergence, exact-head merge and exact-main advancement without exercising the new Simple LIVE path.

### `LIVE_CANARY_READY`

This phase is only for a consumer that has already passed source-only Queue canary acceptance and is preparing the separately gated A8 LIVE canary.

Exactly one final-live mode must be selected:

- `SIMPLE_LIVE_OWNER_DRIVEN`; or
- `AUTO_LIVE_V1_STATIC` when the consumer intentionally keeps its already-reviewed Auto-Live path for that operation.

`DISABLED` is not valid for `LIVE_CANARY_READY`.

Selecting a mode in source does not itself authorize a live mutation. Simple LIVE still requires its exact owner `LIVE <binding_sha256>` decision. Deferred RPi5 execution still requires the existing repository-local LIVE-AUTH v1 protocol.

### `MIGRATED`

The repository has completed the applicable Queue canary and any required LIVE acceptance. A source-only/non-production consumer may remain with final-live mode `DISABLED`; a production-bearing operation selects exactly one reviewed final-live mode.

Migration status never weakens repository-local stricter rules.

## Reusable guard workflow

Canonical reusable workflow:

`.github/workflows/auto-run-full-queue-adoption-guard.yml`

Properties:

- trigger: `workflow_call` only;
- permissions: `contents: read`;
- GitHub-hosted runner;
- pinned `actions/checkout`;
- caller checkout has `persist-credentials: false`;
- canonical shared checkout has `persist-credentials: false`;
- canonical checkout ref is the exact SHA supplied by the caller;
- observed canonical checkout HEAD must equal that SHA;
- caller repository identity must equal the manifest repository;
- every caller reference to the reusable guard must equal the manifest SHA;
- no secret inheritance is required;
- no write permission or mutation step exists.

The reusable guard is a **validation dependency**, not an executor or authority source.

## Final-live exclusivity

A consumer adoption selects one final-live behavior for the Queue-controlled operation:

- `DISABLED`;
- `SIMPLE_LIVE_OWNER_DRIVEN`; or
- `AUTO_LIVE_V1_STATIC`.

`double_execution_paths_allowed` must remain false.

A consumer must not create a state where the same merged Queue result can independently trigger both Simple LIVE and Auto-Live mutation paths. Reusing safe Auto-Live primitives inside a single selected rollout path is allowed; running two independent mutation owners is not.

## RPi5 boundary

A6 does not change the RPi5 trust model.

For a deferred trusted RPi5 executor:

- `deferred_rpi5_requires_live_auth_v1` remains true;
- Simple LIVE does not replace LIVE-AUTH v1 owner identity, TTL, replay or executor constraints;
- `ops-workflows` does not gain private keys, credentials, sudo/root helpers, systemd controls, production shell access or database apply logic.

`RPi5_main` remains the trusted production/host execution boundary.

## Failure semantics

The guard fails closed on at least:

- missing or malformed manifest;
- mutable/malformed shared SHA;
- caller repository mismatch;
- caller workflow pin mismatch;
- more than ten queued items declared by the consumer contract;
- more than one ACTIVE item allowed;
- Queue LIVE authority enabled;
- source-only canary with final LIVE enabled;
- LIVE canary without one explicit final-live mode;
- double final-live path allowed;
- deferred RPi5 LIVE-AUTH bypass;
- A1-A5/Auto-Live composition drift;
- unknown manifest fields or modes.

A CI guard failure is source evidence only. It does not authorize retrying a production mutation, changing repository settings, or selecting an alternate live path.

## A7 handoff

After A6 is merged and exact-main CI is green, A7 may select one canary consumer and create a normal source PR that:

1. pins the accepted A6 `ops-workflows` commit SHA;
2. adds the repository-local adoption manifest with phase `SOURCE_ONLY_CANARY`;
3. calls the reusable adoption guard at the same exact SHA;
4. preserves final LIVE as disabled for the Queue canary;
5. adds only the consumer-local controller/routing changes required to exercise Queue source behavior;
6. reaches Ready under that consumer's normal source rules;
7. does not perform LIVE/runtime/credential/repository-settings mutation as part of the adoption PR.

A7 is a new repository-specific migration action and must freshly read that consumer's rules before any write.
