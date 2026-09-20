# SIMPLE-DEPLOY v1

**Status:** shared source contract; consumer activation is separate
**Canonical repository:** `rozkalnsandris/ops-workflows`
**Machine policy:** `policy/simple-deploy-v1.json`
**Consumer schema:** `policy/schemas/simple-deploy-consumer-v1.schema.json`
**Reusable workflow:** `.github/workflows/simple-deploy.yml`
**Implementation tracker:** `ops-workflows#97`

## 1. Purpose and activation boundary

SIMPLE-DEPLOY v1 is the shared GitHub-side implementation for ordinary Docker/Compose application releases that fit the reviewed `AUTO_DEPLOY_SAFE` profile.

It centralizes the common source-to-registry path:

```text
exact merged consumer SHA
-> validated .simple-deploy.json
-> GitHub-hosted ARM64 build
-> GHCR exact-SHA image
-> immutable registry digest
-> production discovery pointer
-> public-safe intent/receipt
-> trusted runtime reconciliation
```

The shared source contract is not itself a production activation. Merging it does not migrate a consumer, install an RPi5 executor, enable a target, change repository/environment settings, or authorize DB/data/network/secret/host mutation.

Every existing consumer keeps its current repository-local deployment rules until it separately adopts an accepted immutable SIMPLE-DEPLOY revision and completes its reviewed one-time runtime cutover.

## 2. Responsibility boundary

### `ops-workflows`

Owns:

- the reusable GitHub Actions workflow;
- consumer-manifest validation;
- GitHub-hosted image build and GHCR publication;
- exact source-SHA and immutable digest identity rules;
- `production` pointer promotion;
- `environment: production` integration;
- one shared target-concurrency model;
- deterministic public-safe deployment intent output;
- immutable shared-pin and fleet-upgrade rules.

It does **not** own:

- RPi5 credentials, private keys, Docker socket/root authority or systemd units;
- arbitrary SSH, shell, argv or host-path execution;
- production Compose execution;
- application database/schema/data mutation;
- Cloudflare/DNS/network mutation;
- consumer secrets or private runtime configuration.

### Consumer repository

A consumer owns only application-specific reviewed configuration and application contracts:

- one tiny caller pinned to an immutable full commit SHA;
- one fixed `.simple-deploy.json` manifest;
- its Dockerfile/build context;
- Compose project/file/service identities;
- target alias and runtime class;
- liveness/readiness paths;
- persistent-volume identities;
- the explicit pull profile and sensitive-operation exclusions.

A consumer must not copy the shared build/publish/promotion algorithm or add a competing generic production-concurrency controller.

### Trusted runtime

`rozkalnsandris/RPi5_main#666` owns the generic allowlisted RPi5 pull deployer. It resolves the stable production pointer to one digest, freezes that digest for an attempt, performs the fixed Compose lifecycle, verifies health/readiness and records deployed digest/source evidence.

SIMPLE-DEPLOY does not turn GitHub prose or workflow inputs into arbitrary host authority.

## 3. Consumer manifest

The only accepted consumer manifest path is:

```text
.simple-deploy.json
```

The schema is deliberately narrow and fail-closed. Unknown fields are rejected. In particular, a manifest cannot add generic command, argv, environment, secret, credential, hook, arbitrary host-path or dynamic operation-graph fields.

Required identities include:

- schema `rozkalns.simple-deploy.consumer.v1`;
- exact `owner/repository` identity;
- caller-bound `ghcr.io/<owner>/<repository>` image identity;
- build context and Dockerfile as safe repository-relative paths;
- architecture `linux/arm64` in v1;
- target alias and fixed runtime class `rpi5-compose`;
- Compose project/file/service identity for the trusted allowlist handoff;
- fixed liveness path;
- readiness either `required` with a fixed path or explicit `not-applicable`;
- an explicit persistent-volume identity list, including `[]` when the service has no persistent volumes;
- runtime pull profile;
- the complete fixed sensitive-operation exclusion set.

The required exclusion set is:

```text
database-schema-data-mutation
destructive-recovery
secrets-credentials-permissions
cloudflare-dns-network
private-provider-activation
unrelated-host-control
```

Ordinary SIMPLE-DEPLOY therefore cannot silently absorb database/schema/data migration, recovery, credentials, Cloudflare/DNS/network work, private-provider activation or unrelated host-control changes.

## 4. Reusable workflow entry contract

The reusable workflow is callable only through `workflow_call` and accepts one runtime input:

```text
source_sha
```

`source_sha` must be a full 40-character commit SHA, must equal the caller event SHA, must be the checked-out SHA and must come from the caller repository default branch. Pull-request merge refs and floating caller targets fail closed.

The workflow reads the consumer configuration only from the reviewed `.simple-deploy.json` at that exact source revision.

The reusable workflow identifies its own source using the reusable job identity (`job.workflow_repository` + `job.workflow_sha`) and checks out the shared validator at that same exact revision. The shared revision is therefore part of the deployment evidence rather than a mutable `main` assumption.

## 5. Runner and permission contract

Public consumers use GitHub-hosted `ubuntu-24.04` runners. Persistent privileged RPi5 self-hosted runners are outside this contract.

The caller grants only:

```yaml
permissions:
  contents: read
  packages: write
```

The called workflow cannot elevate beyond caller-granted `GITHUB_TOKEN` permissions. `permissions: write-all` is forbidden.

`packages: write` is used only to publish the caller-bound GHCR package and advance its stable discovery pointer. The workflow accepts no RPi5 credential and no runtime registry credential.

## 6. Image build and immutable identity

SIMPLE-DEPLOY v1 builds `linux/arm64` on GitHub-hosted runners using immutable-SHA-pinned setup actions.

For exact consumer SHA `<source_sha>`, the workflow publishes:

```text
ghcr.io/<owner>/<repository>:<source_sha>
```

Build metadata must produce an immutable digest matching:

```text
sha256:<64 lowercase hexadecimal characters>
```

That exact resolved digest is the deployment identity. The source-SHA tag is useful source correlation; it is not a substitute for the digest in the runtime receipt.

The image also receives public-safe OCI labels for the consumer source SHA, target alias and accepted shared workflow revision.

## 7. Production pointer is discovery only

The stable pointer is:

```text
ghcr.io/<owner>/<repository>:production
```

`production` is discovery only. The exact resolved digest is the deployment identity.

Promotion happens only after the exact-SHA image build/push succeeds and yields a valid digest. The workflow then uses registry manifest tooling to point `:production` at the already-built `image@sha256:...`; it does not rebuild the application for promotion.

Promotion is required to preserve the original digest. If the promoted descriptor digest differs from the built digest, the workflow fails closed.

The RPi5 deployer must resolve the pointer before its first runtime mutation and freeze the resulting digest for that attempt. If the pointer later advances, the newer digest waits for a later reconciliation rather than replacing the in-flight candidate.

## 8. `environment: production`

The mutation-capable publish/promotion job references `environment: production` for GitHub deployment visibility and repository-local environment policy.

A manual required reviewer is not part of the baseline one-approval `AUTO_DEPLOY_SAFE` UX. A repository may deliberately configure stricter environment protection, but doing so adds a repository-local gate and changes that consumer's UX; the shared workflow does not create, remove or modify environment settings.

## 9. Central target concurrency

The called workflow owns production concurrency.

After manifest validation it serializes the mutation-capable publish/promotion job on the validated target alias using the shared `simple-deploy-<target>` key. `cancel-in-progress` is false so an in-flight mutation-capable job is never cancelled by a newer run.

Consumer callers must not define a competing generic production concurrency controller around the reusable workflow. Repository-local unrelated CI concurrency remains outside this rule.

## 10. Public-safe intent

A successful shared run emits a deterministic `rozkalns.simple-deploy.intent.v1` JSON output and job summary containing public-safe identities only:

- consumer repository;
- exact consumer source SHA;
- image repository;
- immutable image digest and `image@digest` reference;
- stable production discovery pointer;
- target alias;
- canonical manifest SHA-256;
- Compose identity;
- liveness/readiness identity;
- persistent-volume identities;
- pull profile;
- exact shared workflow repository and commit SHA.

No credentials, private environment data or host secrets belong in this intent.

The intent is evidence/handoff metadata. It is not arbitrary runtime command authority; `RPi5_main#666` remains responsible for matching target aliases to its own static trusted allowlist.

## 11. GHCR pull profiles

The manifest must select exactly one runtime pull profile:

- `public-anonymous-pull` — preferred for public consumer images containing no private runtime configuration; the trusted runtime can pull without registry credentials.
- `private-read-only` — records that a separately reviewed least-privilege runtime auth profile is required.

The shared public baseline does not accept, generate, rotate, copy or expose private runtime registry credentials. Selecting `private-read-only` never creates that credential profile automatically.

Package visibility itself is repository/package configuration and is not mutated by SIMPLE-DEPLOY source adoption.

## 12. Failure semantics

Before registry mutation, validation failures leave the release unpromoted and fail closed.

The exact image digest is frozen after build publication. The promotion step may point only `:production` at that digest. No alternate image/tag, arbitrary retry loop, destructive cleanup or fallback deploy path is part of v1.

After any state-changing publication/promotion step has begun, unexpected state, digest mismatch, timeout or ambiguity stops the workflow and preserves normal GitHub Actions evidence. The shared workflow does not automatically roll back runtime state, delete packages, mutate persistent data or choose another candidate.

Trusted-runtime post-mutation failure semantics remain owned by `RPi5_main#666` and must be at least as strict.

## 13. Consumer immutable pin and Renovate convention

Production consumers reference the shared workflow by immutable full commit SHA. Mutable `@main`, tags and version branches are not production policy identities.

Illustrative tiny caller:

```yaml
name: Deploy application

on:
  push:
    branches: [main]

permissions:
  contents: read
  packages: write

jobs:
  deploy:
    uses: rozkalnsandris/ops-workflows/.github/workflows/simple-deploy.yml@0123456789abcdef0123456789abcdef01234567 # v1.0.0
    with:
      source_sha: ${{ github.sha }}
```

The hexadecimal value is illustrative and must be replaced with the accepted exact `ops-workflows` commit. The `# v1.0.0` comment is the Renovate-compatible human/version tracking convention; it is not the security identity. The full SHA remains authoritative.

Fleet upgrade lifecycle:

```text
shared change
-> shared tests/CI/review
-> merge accepted shared revision
-> Renovate proposes exact-pin consumer PR
-> consumer CI/review
-> guarded consumer merge under local policy
-> consumer now uses the new immutable shared revision
```

A shared merge never instantly changes every production consumer.

## 14. Compatibility with Auto-Live and Simple LIVE

SIMPLE-DEPLOY is the concrete ordinary Docker/Compose `AUTO_DEPLOY_SAFE` profile built from existing Auto-Live invariants: exact source/target identity, full fail-closed classification, stable target serialization, deterministic health evidence and an explicit consumer adoption boundary.

It does not silently disable Auto-Live consumers that have not migrated. Missing SIMPLE-DEPLOY adoption/cutover means the repository's previous deployment contract remains authoritative.

Simple LIVE remains available for sensitive or exceptional mutation classes. After a target has explicitly completed SIMPLE-DEPLOY activation, an ordinary application image release does not require a fresh per-release Simple LIVE decision. Database/schema/data operations, destructive recovery, secrets/credentials/permissions, Cloudflare/DNS/network, private-provider activation and unrelated host-control work remain separately exact-gated.

`GITHUB-ONLY / LIVE-ALL` remains compatibility/history during controlled migration and for operations that genuinely remain deferred.

## 15. Runtime and canary handoff

The implementation sequence remains serial:

```text
ops-workflows#97 shared source contract
-> RPi5_main#666 generic trusted pull deployer source
-> rozkalns_weather#142 first consumer/canary source adoption
-> one explicit Weather/RPi5 cutover LIVE gate
-> prove merge -> GHCR -> exact digest -> pull deploy -> health/readiness
-> migrate/test other compatible consumers
-> declare SIMPLE-DEPLOY stable/default
-> only then AUTO-RUN FULL Queue vNext #96
```

`RPi5_main#666` consumes only identities already present in its reviewed allowlist. GitHub-side source cannot dynamically select arbitrary Compose projects/services/paths/commands on the host.

Weather `rozkalns_weather#142` is the first canary and must remain a consumer of this shared implementation rather than recreating a Weather-specific build/promotion/deploy engine.

Queue vNext #96 remains blocked until SIMPLE-DEPLOY has stable fleet evidence. This contract does not activate future queue-wide merge/deploy authority.

## 16. Source acceptance

The shared source contract is acceptable only when focused policy tests and repository CI prove:

- `workflow_call` and the fixed input surface remain intact;
- public build/publish uses GitHub-hosted runners;
- every external Action is pinned to a full immutable commit SHA with a tracking comment;
- caller permissions remain `contents: read` + `packages: write`;
- source SHA is exact/default-branch bound;
- exact-SHA image publication and immutable digest capture exist;
- `production` remains discovery only and promotion preserves the exact digest;
- `environment: production` is present;
- the called workflow is the single generic target-concurrency owner;
- manifest unknown/command/secret/traversal fields fail closed;
- target/image/health/readiness/persistence identities are explicit;
- full immutable consumer pin + version-comment convention is documented;
- no RPi5 credential/private runtime configuration is accepted or emitted;
- ordinary deployment excludes sensitive mutation classes;
- Auto-Live/Simple LIVE compatibility remains explicit;
- #666, #142 and post-fleet Queue vNext #96 boundaries remain intact.
