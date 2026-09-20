# Delivery platform roadmap — SIMPLE-DEPLOY first, Queue vNext second

**Status:** canonical planning/sequence document; implementation not yet active  
**Repository:** `rozkalnsandris/ops-workflows`  
**Current shared implementation issue:** `#97`  
**Architecture umbrella:** `#94`  
**Generic RPi5 executor:** `rozkalnsandris/RPi5_main#666`  
**First consumer/canary:** `rozkalnsandris/rozkalns_weather#142`  
**Post-fleet next phase:** `#96`

## 1. Canonical objective

Compatible `rozkalnsandris` services should share one normal deployment platform rather than invent a new deployment control plane in every repository.

The steady-state ordinary release target is:

```text
AUTO-RUN FULL
-> exact-head CI PASS
-> guarded merge
-> tiny consumer caller
-> shared SIMPLE-DEPLOY reusable workflow
-> GitHub-hosted image build
-> GHCR exact Git SHA + immutable image digest
-> stable production desired-digest pointer
-> generic trusted RPi5 pull deployer
-> docker compose pull / up -d --wait
-> health/readiness
-> deployed digest receipt
-> LIVE
```

After one-time consumer activation, an ordinary `AUTO_DEPLOY_SAFE` release should not require a second per-release LIVE approval.

Sensitive/non-standard operations remain separately gated.

## 2. Canonical ownership

### `ops-workflows`

Owns only reusable GitHub-side implementation and policy:

- `workflow_call` SIMPLE-DEPLOY workflow;
- consumer manifest/schema validation;
- GitHub-hosted image build;
- GHCR publish/promotion;
- exact source SHA + immutable digest identity;
- `environment: production` integration;
- centrally defined target concurrency;
- public-safe deployment intent/receipt;
- immutable shared SHA pin convention;
- Renovate-compatible fleet upgrade convention;
- shared tests and policy gates.

It does **not** own RPi5 credentials/root helpers, arbitrary SSH/shell, Docker/systemd host mutation implementation, DB apply logic or private runtime configuration.

### `RPi5_main`

Owns one generic trusted allowlisted pull deployer (`#666`) for compatible services.

It performs only fixed reviewed host-side operations derived from static allowlisted manifests and exact resolved image digests.

### Consumer repositories

Own only:

- tiny caller pinned to an immutable accepted `ops-workflows` commit SHA;
- one consumer SIMPLE-DEPLOY manifest;
- normal Dockerfile/Compose/application health contract;
- application-specific persistence and sensitive-operation exclusions.

Consumers must not copy the generic build/publish/promotion/deploy algorithm.

## 3. Exact image identity

A mutable channel/tag such as `production` is **discovery only**.

Canonical deployment identity is the immutable GHCR digest:

```text
sha256:...
```

The runtime sequence is:

```text
read allowlisted production pointer
-> resolve to one digest
-> compare with deployed digest
-> same digest: no-op
-> new digest: freeze that digest for this attempt
-> pull/deploy the exact digest
-> verify health/readiness
-> record exact digest/revision receipt
```

If the pointer moves again while an attempt is in progress, the newer release waits for the next reconciliation. Never silently switch candidate mid-deploy.

## 4. GHCR visibility profiles

For public application repositories whose built images contain no private runtime configuration, prefer a **public GHCR package** so RPi5 can pull anonymously.

This keeps ordinary public-service deployment credential-free on the host.

If a future consumer needs a private image, use a separately reviewed least-privilege read-only registry-auth profile. Private registry credentials must never be placed in public repo issues, manifests, workflow summaries or `ops-workflows` source.

## 5. Reusable workflow permissions

The reusable workflow must operate within caller-granted permissions. The shared contract must document the minimum caller permissions, normally including:

```yaml
permissions:
  contents: read
  packages: write
```

Add only permissions proven necessary by the implementation. `permissions: write-all` is forbidden by the public baseline.

No consumer caller may provide arbitrary production host credentials or commands.

## 6. `production` environment semantics

The shared workflow should reference GitHub `environment: production` for deployment history and policy integration.

For the baseline one-approval `AUTO_DEPLOY_SAFE` flow, the environment must **not** silently add a manual required-reviewer gate. A consumer may intentionally configure stricter protection, but doing so changes that consumer's UX and is not the shared one-approval default.

Environment usage never turns GitHub Actions into the trusted RPi5 execution boundary.

## 7. Concurrency ownership

Production concurrency has one shared owner.

The shared implementation defines a stable target-specific concurrency key so the same production target cannot receive two simultaneous promotions/reconciliations.

Consumer callers must not duplicate a generic caller-side concurrency controller that could cancel/deadlock the called workflow. Any consumer-specific extra serialization must be explicitly justified and tested.

Concurrency does not replace exact digest/baseline revalidation.

## 8. Immutable shared pin + Renovate upgrades

Production callers pin the shared workflow to a full immutable `ops-workflows` commit SHA, never mutable `@main`.

Use a Renovate-compatible version comment/tag convention, conceptually:

```yaml
uses: rozkalnsandris/ops-workflows/.github/workflows/simple-deploy.yml@<40-char-SHA> # v1.x.y
```

The full SHA remains the actual security/runtime identity. The version comment exists only to let Renovate discover a newer accepted release and open a normal consumer PR.

Fleet upgrade path:

```text
shared change
-> shared tests/canary
-> merge
-> Renovate pin-update PRs
-> consumer CI
-> guarded merge where local policy permits
-> consumer moves to new immutable shared SHA
```

Do not use mutable `@main` to create instant fleet-wide blast radius.

## 9. Public repository runner boundary

Public consumer repositories use GitHub-hosted runners for build/publish.

Do not attach a normal persistent privileged self-hosted GitHub Actions runner to RPi5 for public repos.

Trusted production mutation stays in `RPi5_main` behind the fixed allowlisted pull deployer.

## 10. Ordinary deploy vs sensitive operations

Ordinary SIMPLE-DEPLOY is only:

```text
immutable image promotion
+ fixed Compose application lifecycle
+ liveness/readiness verification
+ deployed digest receipt
```

It does not imply or silently include:

- first DB/schema initialization;
- schema/data migration;
- historical backfill/corpus bootstrap;
- destructive DB recovery/restore/delete;
- credentials/secrets/permissions;
- Cloudflare/DNS/network mutation;
- private provider activation;
- arbitrary package/systemd/root work unrelated to the fixed deployer.

These remain separate operation classes and owner gates.

## 11. Failure model

Before mutation, bounded read-only checks may fail with production unchanged.

After the first production mutation starts:

```text
unexpected state / timeout / ambiguity / identity mismatch / health regression
-> preserve minimum public-safe evidence
-> STOP target
```

No undeclared destructive rollback, cleanup, alternate image/tag, arbitrary retry loop or unrelated host recovery is allowed.

A deployment failure never grants DB/network/secret/destructive authority.

## 12. Platform implementation sequence

Canonical order:

```text
1. ops-workflows#97
   implement shared SIMPLE-DEPLOY workflow/policy/schema/tests

2. RPi5_main#666
   implement generic trusted pull deployer source/tests

3. Weather#142
   first consumer/canary: tiny caller + manifest + Compose/policy reconciliation

4. one explicit Weather/RPi5 cutover LIVE gate
   install/enable generic deployer + activate Weather target

5. prove end-to-end Weather release
   merge -> GHCR -> exact digest -> pull deploy -> health/readiness receipt

6. migrate existing compatible services
   Hermes Deals first, then other Docker/Compose services

7. prove at least one non-Weather consumer and declare SIMPLE-DEPLOY stable/default

8. ONLY THEN ops-workflows#96
   AUTO-RUN FULL Queue vNext
```

Do not run Queue vNext in parallel with SIMPLE-DEPLOY platform/canary rollout.

## 13. AUTO-RUN FULL Queue vNext after fleet rollout

Existing `AUTO-RUN FULL Queue v1` / A1 documents remain source-policy design and are not active consumer authority.

`ops-workflows#96` records the **future vNext** target after SIMPLE-DEPLOY is proven across intended consumers.

Desired later UX:

```text
AUTO-RUN FULL QUEUE repo #101 #102 #103 #104

#101 -> source -> CI -> merge -> SIMPLE-DEPLOY -> receipt -> DONE
      -> #102 automatically
#102 -> source -> CI -> merge -> SIMPLE-DEPLOY -> receipt -> DONE
      -> #103 automatically
...
```

One explicit queue activation freezes the exact ordered issue set and ordinary allowed risk envelope. No approval is needed between normal successful items.

The queue interrupts the owner only for a genuine problem/gate such as scope/risk expansion, unresolved CI/review failure, unsafe merge conflict, DB/schema/data requirement, secret/permission/network/host-control requirement, destructive recovery, SIMPLE-DEPLOY fail-closed state or authorization ambiguity.

Current A1's final owner LIVE model remains historical/current-design behavior until #96 is explicitly implemented and adopted after fleet stability. No current shared-policy edit silently grants queue-wide merge or LIVE authority.

## 14. New-project default after platform acceptance

A future compatible service should need approximately:

```text
Dockerfile
Compose production contract
.simple-deploy.json
.github/workflows/deploy.yml   # tiny caller only
```

No new project should design another ordinary RPi5 deployment framework unless it provably cannot fit the accepted SIMPLE-DEPLOY profile.

## 15. Completion conditions for the platform roadmap

The SIMPLE-DEPLOY phase is complete only when:

- shared reusable workflow/policy/schema/tests are accepted;
- generic RPi5 deployer is accepted and activated;
- Weather canary proves end-to-end automatic ordinary release;
- at least one non-Weather consumer proves reuse;
- intended compatible existing services are migrated or explicitly classified non-compatible;
- new compatible projects have a documented bootstrap template;
- legacy per-project ordinary deployment frameworks are marked historical/superseded after migration receipts;
- ordinary release UX is stable enough to make #96 the next platform priority.

Only then should AUTO-RUN FULL Queue vNext become active implementation work.
