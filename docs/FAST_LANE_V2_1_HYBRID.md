# FAST-LANE v2.1 Hybrid

This is the canonical cross-project delivery policy for repositories owned by `rozkalnsandris`.

## Goal

Shorten the path from a clear task to a reviewed result without weakening production, host, credential, data-write, or trust-boundary gates. Repository-local rules may be stricter; a local stricter rule always wins.

## Two operator lanes

### FAST

Use FAST for source-only work that does not create or activate a new trust boundary or live capability. Typical examples are documentation, tests, UI/source changes, parsers, deterministic refactors, and other changes whose effects remain inside Git/CI until a later separately authorized action.

A FAST authorization may cover one coherent execution batch from fresh repository state through Ready for review:

`fresh state -> one branch -> implementation -> focused validation -> push -> Draft PR -> selective CI -> bounded corrections -> relevant Ready validation -> one Ready receipt -> STOP`

FAST never authorizes merge, production deployment, production database writes/migrations, host/root mutation, service activation/restart, secrets/credentials, Cloudflare mutation, firmware flash/OTA, physical actuation, or another live write.

### STRICT

Use STRICT when work reaches a live/runtime authority boundary or changes the mechanism that can reach one. Examples include production deploy/apply, database migration/write, host/root/systemd/Docker/network changes, credential or secret operations, Cloudflare production changes, retained-evidence writes, self-hosted-runner authority, firmware flash/OTA, live MQTT/device commands, or first activation of a privileged capability.

Source code that prepares a future STRICT operation may still be developed in a source-only PR, but activation remains separately authorized.

## Related-work batching

A FAST PR may combine 2-5 closely related work items when all of the following hold:

- one subsystem or coherent acceptance story;
- the same risk class;
- no new trust boundary;
- no production/live mutation;
- review remains understandable as one change.

Do not batch unrelated cleanup or mix a low-risk change with a first-time privileged capability merely to reduce PR count.

## Bounded corrective commits

After the first successful publication of a FAST branch/PR, up to two scope-preserving corrective commits may be made without a new owner authorization when CI or review proves a defect inside the already authorized scope.

STOP for new authorization if:

- a third corrective commit is required;
- the intended scope expands materially;
- a migration, permission, secret, runtime, host, production, or trust-boundary change appears;
- a GitHub write itself returns an ambiguous or failed result.

A test failure is validation evidence, not permission to broaden scope.

## CI model

Workflows should start normally and classify changed files inside the workflow. Prefer job-level conditions over top-level `paths`/`paths-ignore` for checks that may become required.

Recommended layers:

1. `classify` - deterministic changed-file/risk classification;
2. FAST feedback - syntax/static/focused affected tests;
3. Ready validation - full relevant subsystem acceptance;
4. `FAST-LANE Merge Gate` - one stable final status over required jobs.

Skipped-by-design jobs are acceptable only when the classifier proves they are irrelevant. Security/policy checks that protect public information, credentials, workflow authority, or a release trust contract must not be skipped merely for speed.

A repository may keep full CI on every `main` push when deployment or release authorization depends on exact-main push evidence.

## Evidence and continuity

Do not repeat a full mutable-state receipt after every micro-step.

Create one Ready receipt containing at least:

- lane and related work;
- base and exact head SHA;
- reviewed diff/scope;
- relevant CI/check results;
- unresolved review-thread count;
- runtime/deploy/migration/trust-boundary classification;
- exact next gate.

Immediately before merge, refresh only mutable merge evidence: current base/main, exact PR head, mergeability, CI/checks, reviews/threads, and policy state.

Each project should maintain one concise CURRENT continuity location when continuity is useful. Update it at meaningful gate/phase transitions, not after every commit. PRs, issues, CI and immutable artifacts remain the detailed evidence sources.

## Merge and live mutations

Merge always requires an explicit owner merge instruction unless a repository has a separately authorized and technically enforced exact-head auto-merge policy.

Merge authorization does not authorize deployment, migration, retained-data writes, host mutation, secrets, Cloudflare changes, firmware activation, or another live mutation.

After an authorized live mutation starts, any error or ambiguous outcome requires evidence preservation and STOP. Do not retry, roll back, clean up, or choose an alternate mutation path without new authorization unless the exact operation contract explicitly pre-authorized that behavior.

## Cross-project consistency

All adopting repositories use the same external terms (`FAST`, `STRICT`, Ready receipt, bounded corrections, explicit merge gate). Project-specific examples and CI classifiers remain local because a parser, web UI, Home Assistant config, Cloudflare Worker, RPi host repo, and ESP32 firmware do not share the same runtime risk boundary.

The machine-readable defaults are in `policy/fast-lane-v2.1.json`. Repository-local policy may only tighten these defaults unless an owner explicitly changes this canonical standard.
