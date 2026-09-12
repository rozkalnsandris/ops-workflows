# AUTO-RUN FULL Queue reusable guards v1 — A6

**Status:** shared source-policy / read-only CI guard contract; consumer activation remains explicit.  
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
- `LIVE_CANARY_READY` and `MIGRATED` require an explicit source-canary completion evidence block rather than a phase label alone;
- source-canary evidence is historical proof, never LIVE authority;
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

The manifest is intentionally bounded. It records the migration phase, the public-safe source-canary proof needed for later phases, and the shared trust-boundary assertions needed to prove that the consumer is adopting the same Queue semantics. It is not a deployment operation registry and must not contain credentials or protected runtime data.

### Required identity binding

The manifest binds:

- exact caller repository;
- exact immutable 40-character lowercase `ops-workflows` commit SHA;
- one adoption phase;
- Queue authority limits;
- source-canary proof state;
- one final-live mode;
- shared/consumer execution boundaries.

The consumer CI workflow must call:

`rozkalnsandris/ops-workflows/.github/workflows/auto-run-full-queue-adoption-guard.yml@<exact-40-char-sha>`

Every caller workflow reference to this guard must use the same exact SHA recorded by the manifest. Mutable `main`, tags or version branches are rejected.

### Source-canary evidence gate

The manifest contains one exact `source_canary` object. Its status is either:

- `NOT_PROVEN`; or
- `QUEUE_SOURCE_COMPLETE`.

`NOT_PROVEN` is deliberately empty: Queue ID, controller issue, ordered issue list, main SHAs and receipt digests must all be null/empty. This prevents a partial or implied canary from being mistaken for completion.

`QUEUE_SOURCE_COMPLETE` is a reviewed source attestation and must bind all of:

- one bounded public-safe Queue ID;
- the durable Queue controller issue number;
- the exact ordered 1-10 issue set that was exercised;
- exact activation-main SHA;
- exact final-main SHA after Queue source completion;
- SHA-256 of the durable Queue authorization receipt;
- SHA-256 of the final Queue source-completion receipt.

Issue numbers must be positive and unique. SHAs and receipt hashes must be lowercase exact-length values. The evidence block contains no secrets or runtime credentials.

A source-only consumer may record `QUEUE_SOURCE_COMPLETE` while final LIVE remains disabled. However `LIVE_CANARY_READY` and `MIGRATED` **must** carry `QUEUE_SOURCE_COMPLETE`; a phase label without this evidence fails closed.

The checked-in evidence block does not create Queue or LIVE authority and does not replace the underlying durable GitHub receipts. It is the source-policy binding that prevents a consumer from claiming later migration phases merely because adoption plumbing was merged.

Consumers pinned to an older immutable shared SHA are unaffected until they explicitly repin. A consumer repinning to a shared revision containing this guard must add the `source_canary` block and satisfy the phase/evidence rules in the same reviewed source change.

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

Merging Queue adoption plumbing alone does not prove that canary. Until an actual Queue source run has completed, the manifest remains `source_canary.status=NOT_PROVEN`. After a genuine Queue run reaches source completion, the consumer may record `QUEUE_SOURCE_COMPLETE` while still in this phase before a separately reviewed phase advance.

### `LIVE_CANARY_READY`

This phase is only for a consumer that has already passed source-only Queue canary acceptance and has `source_canary.status=QUEUE_SOURCE_COMPLETE`.

Exactly one final-live mode must be selected:

- `SIMPLE_LIVE_OWNER_DRIVEN`; or
- `AUTO_LIVE_V1_STATIC` when the consumer intentionally keeps its already-reviewed Auto-Live path for that operation.

`DISABLED` is not valid for `LIVE_CANARY_READY`.

Selecting a mode in source does not itself authorize a live mutation. Simple LIVE still requires its exact owner `LIVE <binding_sha256>` decision. Deferred RPi5 execution still requires the existing repository-local LIVE-AUTH v1 protocol.

### `MIGRATED`

The repository has completed the applicable Queue source canary and therefore must also carry `source_canary.status=QUEUE_SOURCE_COMPLETE`. Any required LIVE acceptance remains governed by the selected consumer path and repository-local rules.

A source-only/non-production consumer may remain with final-live mode `DISABLED`; a production-bearing operation selects exactly one reviewed final-live mode.

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
- adoption phase and source-canary evidence must be internally consistent;
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
- malformed or partially populated source-canary evidence;
- `LIVE_CANARY_READY` without `QUEUE_SOURCE_COMPLETE` evidence;
- `MIGRATED` without `QUEUE_SOURCE_COMPLETE` evidence;
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
2. adds the repository-local adoption manifest with phase `SOURCE_ONLY_CANARY` and `source_canary.status=NOT_PROVEN`;
3. calls the reusable adoption guard at the same exact SHA;
4. preserves final LIVE as disabled for the Queue canary;
5. adds only the consumer-local controller/routing changes required to exercise Queue source behavior;
6. reaches Ready under that consumer's normal source rules;
7. does not perform LIVE/runtime/credential/repository-settings mutation as part of the adoption PR.

A7 adoption is readiness to exercise the source-only Queue canary, not proof that the canary already ran. Only a genuine Queue execution that reaches source completion may populate `QUEUE_SOURCE_COMPLETE`; only after that proof exists may a later source change advance to `LIVE_CANARY_READY`.

A7 is a new repository-specific migration action and must freshly read that consumer's rules before any write.
