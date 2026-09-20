# SIMPLE-DEPLOY v1 — shared deployment platform plan

**Status:** DESIGN / NOT ACTIVE  
**Canonical repository:** `rozkalnsandris/ops-workflows`  
**Tracking issue:** `#94`  
**First planned canary:** `rozkalnsandris/rozkalns_weather#142`  
**Trusted RPi5 execution boundary:** `rozkalnsandris/RPi5_main`

## 1. Objective

Create one shared deployment standard for compatible current and future `rozkalnsandris` services so individual application repositories provide deployment **configuration**, not independent deployment frameworks.

Target ordinary-release flow:

```text
AUTO-RUN FULL
-> exact-head CI PASS
-> merge to main
-> shared SIMPLE-DEPLOY v1
-> GitHub-hosted build
-> GHCR immutable exact-SHA image + digest
-> production promotion
-> trusted runtime pull deploy
-> docker compose up --wait
-> health/readiness verification
-> LIVE
```

After a consumer has completed its one-time SIMPLE-DEPLOY adoption/cutover, an ordinary application release should not require a project-specific broker/operator/JIT/deploy-queue control plane or a new manual LIVE approval for every normal release.

This document is a design plan only. It does not activate automatic production mutation, install an RPi5 executor, change repository permissions, mutate a database, change Cloudflare/network state, or alter credentials/secrets.

## 2. Design principles

1. **One implementation, many consumers.** Common build/publish/promotion/deploy policy belongs in `ops-workflows`.
2. **Configuration stays local.** Consumer repositories declare only application-specific identities and constraints.
3. **Build once, deploy exact bytes.** The deployed image is the exact reviewed GHCR digest produced from the merged source revision.
4. **Immutable shared policy identity.** Production consumers pin accepted `ops-workflows` reusable workflows/policy to a full commit SHA.
5. **Central upgrades without central blast radius.** Renovate proposes pin-update PRs in consumers after a new shared revision is validated.
6. **Public-repository safety.** Public consumer repositories use GitHub-hosted build/publish runners; no normal persistent privileged self-hosted RPi5 Actions runner.
7. **Trusted host execution remains separate.** RPi5 credentials/root/Docker/systemd authority remain in `RPi5_main`, not `ops-workflows`.
8. **Ordinary deploy is narrow.** Image/Compose lifecycle and health verification are separate from DB, corpus, private-provider, credential, network and destructive operations.
9. **Fail closed after mutation.** Unexpected state after production mutation begins preserves evidence and stops; no undeclared retry/cleanup/rollback/alternate path.
10. **Do not create another generic deployment engine.** Reuse and simplify the existing Auto-Live/Simple LIVE safety primitives.

## 3. Existing shared foundation

SIMPLE-DEPLOY v1 should evolve the repository's existing delivery work instead of starting a fourth independent system.

### Auto-Live v1

Reuse:

- post-merge reconciliation;
- exact merged source identity;
- exact target/baseline reasoning;
- `AUTO_DEPLOY_SAFE` vs manual/sensitive classes;
- one mutation-capable reconciliation per target;
- fail-closed post-mutation semantics;
- immutable shared policy pinning.

SIMPLE-DEPLOY v1 makes the common safe Docker/Compose application-release class concrete and reusable.

### Simple LIVE

Retain the narrow fixed-operation and explicit-owner-gate model for sensitive or exceptional mutation classes. Ordinary already-activated SIMPLE-DEPLOY application releases should not be forced back through one manual LIVE approval per release.

### FAST-LANE / AUTO-RUN FULL

These remain source/merge governance. For an adopted ordinary SIMPLE-DEPLOY target, merge is the human production decision that triggers the already-reviewed fixed automatic deployment path.

### GITHUB-ONLY / LIVE-ALL

Remain compatibility/history for consumers not yet migrated and for operations that genuinely remain manually deferred. They should not remain the normal app-release path after a service has successfully migrated to SIMPLE-DEPLOY.

## 4. Ownership boundaries

### 4.1 `ops-workflows`

Owns the shared GitHub-side deployment platform:

- normative SIMPLE-DEPLOY documentation;
- machine-readable policy and schemas;
- reusable `workflow_call` deployment workflow(s);
- consumer manifest validation;
- GitHub-hosted image build logic;
- GHCR publish/promotion logic;
- exact-SHA and digest identity requirements;
- GitHub `environment: production` integration;
- stable per-target `concurrency` rules;
- public-safe deployment intent/receipt schema;
- immutable external Action/reusable-workflow pin validation;
- migration/adoption contract;
- Renovate-compatible shared-pin upgrade convention;
- shared tests and policy gates.

`ops-workflows` must **not** store or implement:

- RPi5 credentials/private keys;
- production root/sudo helpers;
- arbitrary SSH or remote shell;
- production Docker/systemd mutation implementation;
- application database apply logic;
- private application runtime configuration;
- Cloudflare secrets;
- arbitrary generic operation graphs.

### 4.2 `RPi5_main`

Owns one generic trusted host-side deployment executor for compatible RPi5 services.

Conceptual service/helper identity:

```text
rozkalns-simple-deployer
```

Responsibilities:

- accept only explicitly allowlisted consumer manifests/targets;
- observe only the fixed approved GHCR image/repository identity;
- compare desired image digest with deployed digest;
- no-op when identical;
- perform fixed Compose lifecycle equivalent to:

```text
docker compose pull
docker compose up -d --wait --wait-timeout <bounded>
```

- verify fixed local liveness/readiness endpoints;
- record deployed digest/revision in fixed local state;
- serialize per target;
- fail closed on unexpected state;
- never accept arbitrary command/argv/path/repository/service/environment authority from GitHub prose or workflow inputs.

RPi5 credentials, Docker socket/root helper, systemd unit, local state and production host evidence remain inside this trusted boundary.

### 4.3 Consumer repositories

A compatible consumer should contain only:

1. a tiny caller workflow pinned to an immutable `ops-workflows` commit SHA;
2. one machine-readable SIMPLE-DEPLOY manifest containing application-specific identities;
3. the normal Dockerfile/Compose/application health contract.

Consumer manifests may define:

- image/repository identity;
- Dockerfile/build context;
- target alias;
- required architecture, initially typically `linux/arm64` for RPi5;
- Compose project/file/service identity;
- health endpoint;
- readiness endpoint where available;
- runtime profile/class;
- persistent volume identities that must survive release replacement;
- explicit sensitive-operation exclusions.

The consumer must **not** copy the common build/publish/promotion/deploy algorithm.

## 5. Shared reusable workflow target

Proposed canonical workflow:

```text
.github/workflows/simple-deploy.yml
```

It should expose `workflow_call` and own the common GitHub-side logic.

For an ordinary merged release it should:

1. bind execution to the exact merged `main` revision;
2. validate the consumer SIMPLE-DEPLOY manifest;
3. require declared exact-SHA CI evidence before production promotion where the adopted contract requires it;
4. use GitHub-hosted runner(s);
5. build the application image for the declared architecture;
6. publish to GHCR using least-privilege GitHub permissions, normally `packages: write` plus required read permissions;
7. tag every release by exact Git SHA;
8. surface the immutable registry digest;
9. advance one stable production channel only to that already-built image;
10. reference `environment: production` for deployment visibility/policy;
11. serialize production work with a stable target concurrency key;
12. emit a deterministic public-safe deployment intent/receipt for the trusted runtime controller;
13. avoid RPi5 credentials and arbitrary remote host execution.

The reusable workflow is shared implementation. The consumer caller should remain intentionally small.

## 6. Production identity

Build once and deploy the exact verified artifact.

Required identities:

- exact consumer Git commit SHA;
- immutable GHCR image digest (`sha256:...`);
- stable production target alias;
- fixed application/service identity;
- exact accepted `ops-workflows` revision.

The RPi5 must pull the published image. It must not rebuild application source during an ordinary production deployment.

## 7. Immutable pinning and fleet upgrades

Production consumers must pin the reusable workflow/policy to a full commit SHA, for example:

```yaml
jobs:
  production:
    uses: rozkalnsandris/ops-workflows/.github/workflows/simple-deploy.yml@<40-char-SHA>
    with:
      profile: rpi5-compose
```

Do **not** use mutable `@main` as the production workflow identity.

Central upgrade lifecycle:

```text
change SIMPLE-DEPLOY in ops-workflows
-> shared CI / policy tests
-> canary validation
-> merge
-> Renovate detects the accepted new shared revision
-> Renovate opens consumer pin-update PRs
-> consumer CI validates each repository
-> guarded auto-merge where local policy permits
-> consumers move to the new shared revision
```

This gives one centrally maintained implementation while limiting fleet-wide blast radius and preserving reproducibility.

## 8. Ordinary deployment boundary

SIMPLE-DEPLOY v1 ordinary application deployment is only:

```text
immutable image promotion
+ Compose application lifecycle
+ liveness/readiness verification
+ deployed-digest receipt
```

It must not silently perform:

- first database/schema initialization;
- normal schema/data migrations unless a future explicitly reviewed migration class opts in;
- historical corpus/data backfill;
- destructive DB recovery/restore/delete;
- private provider activation;
- credentials/secrets/permission mutation;
- Cloudflare/DNS/network mutation;
- arbitrary package/systemd/root changes unrelated to the fixed deployer.

These remain separately classified and gated operations.

## 9. Failure model

Before mutation, a contract may allow a small bounded read-only retry policy when explicitly reviewed.

After the first production mutation starts:

- error, timeout, drift or ambiguity => fail closed;
- preserve public-safe evidence;
- no destructive database rollback;
- no undeclared cleanup;
- no arbitrary alternate deployment path;
- retry or rollback only when explicitly designed, reviewed, bounded and proven safe in the fixed operation contract.

A failed deployment must not create authority for unrelated host recovery or data mutation.

## 10. Public repository safety

A public application repository must not attach a normal persistent privileged self-hosted GitHub Actions runner directly to the RPi5.

Use GitHub-hosted build/publish workflows. Trusted production mutation occurs through the narrow RPi5 controller/deployer owned by `RPi5_main`.

This keeps PR/workflow code away from persistent host privilege while preserving automatic post-merge delivery.

## 11. Proposed canonical shared surfaces

```text
docs/SIMPLE_DEPLOY_V1.md
policy/simple-deploy-v1.json
policy/schemas/simple-deploy-consumer-v1.schema.json
.github/workflows/simple-deploy.yml
.github/workflows/simple-deploy-policy-gate.yml
```

This design document may later be renamed/promoted to the normative `docs/SIMPLE_DEPLOY_V1.md` when the implementation contract is accepted.

Optional supporting files are allowed only when they reduce duplication or improve deterministic validation. Do not recreate a large generic deployment transaction framework.

## 12. Migration plan

### Phase 1 — shared source in `ops-workflows`

- accept this architecture plan;
- promote a normative SIMPLE-DEPLOY document;
- add machine policy/schema;
- implement reusable workflow contract;
- add tests and policy gate;
- reconcile Auto-Live/Simple LIVE compatibility wording;
- document immutable pin + Renovate upgrade convention.

No production mutation occurs in this phase.

### Phase 2 — generic executor in `RPi5_main`

- create one generic simple-deployer source contract;
- implement fixed allowlisted manifest/target handling;
- digest comparison/no-op;
- fixed Compose pull/up/wait;
- health/readiness verification;
- deployed-state receipt;
- fail-closed behavior;
- tests and reviewed one-time installation/cutover contract.

No consumer production cutover occurs without the explicit runtime gate defined by `RPi5_main`.

### Phase 3 — Weather first canary

`rozkalnsandris/rozkalns_weather#142` is the intended first canary.

Weather should adopt the central reusable implementation instead of implementing another project-specific GHCR/deploy framework. Weather remains responsible only for its manifest, Compose/application health contract, persistent SQLite volume invariants and project-specific sensitive-operation separation.

Canary acceptance should prove:

```text
merge
-> central SIMPLE-DEPLOY workflow
-> GHCR exact SHA/digest
-> RPi5 generic pull deployer
-> Compose up --wait
-> /health PASS
-> /ready PASS
-> deployed digest/revision receipt
```

Only after this is proven should Weather's old broker/operator/queue/JIT steady-state deployment path be marked superseded.

### Phase 4 — migrate existing compatible services

Initial candidate order after Weather:

1. Hermes Deals;
2. dashboard/control-plane web services that fit the Docker/Compose profile;
3. other compatible RPi5 Docker web services.

Each existing service receives an explicit adoption/canary. Merging shared policy alone never silently migrates a production consumer.

### Phase 5 — platform default

After Weather plus at least one additional consumer prove reuse:

- SIMPLE-DEPLOY becomes the default deployment standard for compatible `rozkalnsandris` projects;
- new compatible projects start with the shared caller + manifest;
- project-specific normal deployment frameworks are deprecated after migration receipts prove they are unused;
- non-standard/sensitive operations remain explicitly separate.

## 13. New-project bootstrap target

A future compatible service should need approximately:

```text
Dockerfile
compose production contract
.simple-deploy.json
.github/workflows/deploy.yml   # tiny caller only
```

The caller should reference the centrally maintained reusable workflow and contain no copied deployment algorithm.

## 14. Definition of Done for the shared platform

The shared platform is not complete until all of the following are true:

- one normative SIMPLE-DEPLOY document exists;
- one machine-readable policy exists;
- one validated consumer manifest schema exists;
- one reusable GitHub-side workflow owns common deployment logic;
- public consumers use GitHub-hosted build/publish;
- GHCR exact-SHA and digest identity is enforced;
- `environment: production` and stable target concurrency are enforced;
- consumers use immutable shared revision pins;
- Renovate can propose shared-version upgrades;
- one generic RPi5 pull deployer contract exists;
- ordinary app deploy is separated from DB/private/network/credential mutation classes;
- Weather first canary passes end to end;
- at least one additional consumer proves reuse;
- legacy project-specific deploy paths are explicitly historical/compatibility after migration;
- new compatible projects have a documented bootstrap template.

## 15. Non-goals

SIMPLE-DEPLOY v1 is **not**:

- a generic arbitrary remote shell from GitHub;
- a credential store in `ops-workflows`;
- a persistent privileged self-hosted runner on public app repos;
- a mutable `@main` production dependency;
- an implicit fleet-wide runtime migration on shared-policy merge;
- a dynamic transaction engine for arbitrary DB/network/root work;
- a mechanism for hiding migrations/backfills/destructive recovery inside ordinary deployment;
- a reason to delete historical audit evidence during first migration.

## 16. Current activation state

At creation of this plan:

- `ops-workflows/main` source baseline is `30a3075d3959c40ff0cc5516d63dfb341dc04f00`;
- this document is design-only;
- no SIMPLE-DEPLOY consumer is activated by this document;
- no production or RPi5 mutation is authorized;
- existing repository-local deployment contracts remain authoritative until each consumer explicitly adopts the final shared contract.

Tracking and implementation sequencing live in `ops-workflows#94`.
