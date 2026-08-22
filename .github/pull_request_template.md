## FAST-LANE v2.1

- **Lane:** FAST / STRICT
- **Related work:** #...
- **Runtime effect:** NONE / READ_ONLY / MUTATION
- **Deploy required:** YES / NO
- **Migration required:** YES / NO
- **Trust-boundary change:** YES / NO

## Scope

Describe one coherent acceptance story. FAST may batch 2-5 closely related same-risk work items; do not mix unrelated or privileged work merely to reduce PR count.

## Validation

List focused validation first and broader/Ready validation separately.

## Ready receipt

Complete once when the PR is ready for merge consideration:

- Base / current main:
- Exact head SHA:
- CI/checks:
- Unresolved review threads:
- Reviewed scope/diff:
- Runtime/deploy/migration classification:
- Exact next gate:

Merge is not authorized by this PR. A merge never authorizes production deployment, migration, host/root mutation, secrets, Cloudflare mutation, firmware activation, or another live write.
