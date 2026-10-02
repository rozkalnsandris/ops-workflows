# SIMPLE-DEPLOY v1 consumer bootstrap

**Status:** source/bootstrap contract for compatible consumers.  
**Canonical shared policy:** `docs/SIMPLE_DEPLOY_V1.md` + `policy/simple-deploy-v1.json`.  
**Template source:** `templates/simple-deploy/`.  
**Tracking umbrella:** `ops-workflows#94`.

This bootstrap reduces a new compatible consumer to the smallest reviewed surface. It does **not** activate an RPi5 target, grant LIVE authority, create credentials, mutate Docker/systemd, or authorize database/data/network work.

## 1. Compatibility gate

Use this profile only when the service fits the ordinary SIMPLE-DEPLOY v1 envelope:

- public GitHub consumer repository;
- image build can run on a GitHub-hosted runner;
- production image is `linux/arm64`;
- runtime is the fixed `rpi5-compose` class;
- Dockerfile and Compose identities are deterministic;
- liveness is a fixed HTTP path and readiness is either a fixed HTTP path or explicitly `not-applicable`;
- persistent volumes are explicitly named;
- ordinary deploy does not require database/schema/data mutation, destructive recovery, secrets/permissions, Cloudflare/DNS/network mutation, private-provider activation, or unrelated host control.

If any of those conditions do not hold, do not stretch the template into a new deployment engine. Classify the consumer separately.

## 2. Copy the two consumer surfaces

Copy:

```text
templates/simple-deploy/.simple-deploy.json
-> <consumer>/.simple-deploy.json

templates/simple-deploy/.github/workflows/simple-deploy.yml
-> <consumer>/.github/workflows/simple-deploy.yml
```

The consumer also needs its normal application-owned `Dockerfile` and production Compose file.

## 3. Bind the manifest to the consumer

Replace every example identity in `.simple-deploy.json` with the consumer's exact values:

- `repository`: exact `owner/repository`;
- `image`: matching lower-case `ghcr.io/owner/repository`;
- `build.context` and `build.dockerfile`;
- `target.alias`: stable allowlisted runtime target identity;
- `compose.project`, `compose.file`, and `compose.service`;
- fixed `health.liveness_path`;
- readiness `state` plus `path` when required;
- every persistent volume that must survive application replacement;
- `registry.pull_profile`.

Prefer `public-anonymous-pull` for public application images that contain no private runtime configuration. `private-read-only` is a separate reviewed registry-auth profile and does not permit putting registry credentials in the manifest or workflow.

The fixed six `forbidden_operations` are mandatory in v1 and must not be weakened.

## 4. Keep the reusable workflow immutable

The template caller uses a reviewed immutable full `ops-workflows` commit SHA plus a human-readable version comment.

Before adopting the template in a consumer:

1. freshly resolve the currently accepted SIMPLE-DEPLOY shared revision;
2. use the exact 40-character commit SHA;
3. retain the Renovate-compatible version comment;
4. never use `@main`, a mutable tag, or a version branch as production workflow identity.

The checked-in template currently reflects the accepted v1.0.0 shared revision used by the proven Weather consumer. A later accepted shared release should update this template through normal reviewed source change rather than making the consumer mutable.

## 5. Caller contract

The tiny caller must keep:

```yaml
permissions:
  contents: read
  packages: write
```

and pass only:

```yaml
with:
  source_sha: ${{ github.sha }}
```

Do not add arbitrary shell command, host path, argv, environment, secret, credential, SSH, or RPi5 execution inputs. Production concurrency is owned by the called shared workflow; do not add a generic caller concurrency controller that can cancel or deadlock it.

## 6. Source adoption is not runtime activation

A consumer source merge can build/publish its exact image and advance the mutable `production` discovery pointer. The immutable registry digest remains the deployment identity.

That source adoption does **not** by itself prove or authorize RPi5 deployment. One-time target registration/activation remains in the trusted `RPi5_main` boundary and requires the repository-local exact owner gate and minimum-sufficient preflight for that target.

After a target has been explicitly activated, ordinary eligible `AUTO_DEPLOY_SAFE` releases may use the standing SIMPLE-DEPLOY path without a fresh per-release LIVE decision. Sensitive/non-standard operation classes remain separately gated.

## 7. Consumer acceptance checklist

Before treating a consumer as adopted:

- manifest validates against `policy/schemas/simple-deploy-consumer-v1.schema.json`;
- caller uses one immutable full shared SHA and least-privilege permissions;
- consumer exact-head CI/review is green;
- Dockerfile/Compose/image/service/health identities are deterministic;
- persistence identities are explicit;
- public/private registry profile is intentionally selected;
- no secret or protected runtime value is present in source;
- runtime target registration and one-time activation are tracked separately;
- end-to-end runtime reuse is not claimed until fresh trusted evidence proves it.

This template is source-only infrastructure. It never creates LIVE authority by itself.
