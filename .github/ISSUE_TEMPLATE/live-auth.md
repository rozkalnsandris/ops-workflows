---
name: Owner-authorized LIVE-AUTH
about: Materialize one explicit owner live decision for one exact READY queue item.
title: "[LIVE-AUTH][PENDING] "
labels: ""
assignees: ""
---

> **Public repository:** include only public-safe operational metadata. Never include secrets, credentials, private keys, authenticated cookies/storage, protected configuration, private host details, or unredacted sensitive logs.
>
> This template is not authority by itself. Replace every placeholder. LIVE-AUTH is valid only after an explicit current owner live/deploy decision and independent server-metadata / TTL / queue / source / CI / baseline / replay validation.

<!-- rozkalns-live-auth:v1 -->
```json
{
  "schema": "rozkalns.live-auth.v1",
  "request_id": "REPLACE_WITH_CANONICAL_UUIDV4",
  "queue_repository": "rozkalnsandris/ops-workflows",
  "queue_issue": 0,
  "source_repository": "REPLACE_WITH_OWNER_REPOSITORY",
  "source_sha": "REPLACE_WITH_EXACT_40_HEX_SHA",
  "target_alias": "replace-with-public-safe-target-alias",
  "operation_id": "replace.with.reviewed.operation.v1",
  "expected_baseline": {
    "kind": "replace-with-reviewed-baseline-kind",
    "value": "REPLACE_WITH_PUBLIC_SAFE_EXPECTED_BASELINE"
  },
  "mutation_budget": [
    {
      "category": "replace-with-reviewed-category",
      "max_operations": 1
    }
  ],
  "rollback_policy": "NONE",
  "exclusions": [
    "database writes",
    "credential or secret changes",
    "permission or trust-boundary changes",
    "undeclared host or infrastructure changes"
  ],
  "dependencies": []
}
```
<!-- /rozkalns-live-auth:v1 -->

The title target alias must exactly equal `target_alias`. The template intentionally contains invalid placeholders so an unreviewed draft cannot accidentally pass the strict protocol linter.
