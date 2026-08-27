# Owner-authorized LIVE-AUTH v1

**Status:** Source contract  
**Canonical repository:** `rozkalnsandris/ops-workflows`  
**Machine policy:** `policy/live-auth-v1.json`  
**Payload schema:** `policy/schemas/live-auth-v1.schema.json`  
**Receipt schema:** `policy/schemas/deploy-receipt-v1.schema.json`

## 1. Purpose

`[DEPLOY-QUEUE][READY]` means that one exact rollout is eligible for a future owner decision. It is never execution authority by itself.

A pull-based executor that runs later on a trusted RPi5 cannot infer live authority from chat history, a merge, `GITHUB-ONLY`, queue `READY`, a prior `LIVE-ALL`, or executor availability. A separately explicit current owner live decision must be materialized as one GitHub Issue:

```text
[LIVE-AUTH][PENDING] <target_alias>
```

One LIVE-AUTH issue authorizes at most one queue item and one exact operation envelope.

## 2. Authority source

Authority comes from GitHub server metadata plus the exact payload, never from a self-declared actor field.

The future executor must require:

- repository full name `rozkalnsandris/ops-workflows`;
- stable repository ID `1328835922`;
- an open Issue, never a pull request;
- GitHub author `type=User`;
- numeric author ID `277435981`;
- reviewed authorization-surface governance;
- when `performed_via_github_app` is present, a separately reviewed owner-operator integration allowlist;
- fixed 600-second TTL evaluated from GitHub server time;
- exact body and canonical payload digests unchanged immediately before dispatch.

The autonomous executor authorization credential must remain **read-only** on this authorization surface. Giving the validator Issues write authority would violate the independence of the authorization proof.

The read-only lint workflow in this repository is advisory source validation only. It does not create authority and it cannot make an invalid authorization executable.

## 3. When LIVE-AUTH may be created

LIVE-AUTH may be created only after a current explicit owner live/deploy decision and fresh read-only revalidation of the selected queue item.

It is never implied by:

- `START`;
- `turpini`;
- PR Ready;
- merge;
- `GITHUB-ONLY`;
- `[DEPLOY-QUEUE][READY]`;
- a historical authorization;
- a previous chat.

Because v1 TTL is 600 seconds, do not create a LIVE-AUTH issue when the pull executor is known to be unavailable or unlikely to observe/revalidate the request before expiry. Leave the queue item `READY` instead.

Do not create dummy or placeholder LIVE-AUTH issues merely to exercise automation. P9 of `RPi5_main#236` requires a genuine prepared owner decision for the first end-to-end dry-run canary.

## 4. Relationship to `LIVE-ALL`

`LIVE-ALL` remains the owner's batch Composite Live decision for the frozen set of ordinary executable READY queue items selected at command time.

For a **direct same-session executor**, the existing repository-local LIVE-ALL execution contract may be used when that executor can perform the bounded operation immediately.

For the **deferred RPi5 pull executor**, the owner decision must additionally be materialized into one LIVE-AUTH issue per selected queue item. The pull executor accepts the GitHub LIVE-AUTH object, not raw chat context.

This preserves both invariants:

1. `READY` is eligibility only.
2. The later pull executor has an independently persisted, exact, TTL-limited, replay-safe owner authorization object.

Creating a LIVE-AUTH issue is itself an authorization-materialization action. Once a live pull executor exists, it must not be performed under `GITHUB-ONLY` or from a bare continuation command because it can deterministically lead to a later production mutation.

## 5. Exact body format

The Issue body contains exactly one authority block:

````text
<!-- rozkalns-live-auth:v1 -->
```json
{
  "schema": "rozkalns.live-auth.v1",
  "request_id": "01234567-89ab-4cde-8fab-0123456789ab",
  "queue_repository": "rozkalnsandris/ops-workflows",
  "queue_issue": 123,
  "source_repository": "rozkalnsandris/example",
  "source_sha": "0123456789abcdef0123456789abcdef01234567",
  "target_alias": "example-production",
  "operation_id": "example.application-deploy.v1",
  "expected_baseline": {
    "kind": "exact-sha",
    "value": "89abcdef0123456789abcdef0123456789abcdef"
  },
  "mutation_budget": [
    {
      "category": "application-deploy",
      "max_operations": 1
    }
  ],
  "rollback_policy": "NONE",
  "exclusions": [
    "database writes",
    "credential changes",
    "permission changes"
  ],
  "dependencies": []
}
```
<!-- /rozkalns-live-auth:v1 -->
````

The example is illustrative, not an authorization.

The strict source linter rejects malformed markers, duplicate JSON keys, unknown/missing fields, non-canonical UUIDv4, invalid repository/SHA/identifier formats, duplicate mutation categories, invalid operation limits, unsupported rollback policy, and title/target mismatch.

## 6. Queue binding

Before acceptance and again immediately before mutation-capable dispatch, the executor must prove that the referenced queue issue is still open and exactly `READY`.

The LIVE-AUTH payload must exactly bind the queue envelope for:

- source repository;
- exact immutable source SHA;
- target alias;
- operation ID;
- expected baseline;
- mutation budget;
- rollback policy;
- exclusions;
- dependencies.

The queue may describe eligibility. The LIVE-AUTH object records the separate current owner decision to execute that exact envelope.

A `304 Not Modified` response is acceptable only for non-authoritative polling optimization. It is never sufficient for final authorization revalidation.

## 7. Replay and expiry

The local trusted state store owns replay prevention.

- GitHub issue identity and `request_id` are unique execution keys.
- Entry into the future mutation-capable adapter consumes the authorization.
- A consumed request never executes again.
- A crash after consumption does not reopen the authorization.
- Expired, edited, closed, malformed, drifted or previously consumed authorization fails closed.

Comments, reactions, labels, locks or issue edits do not extend the 600-second TTL.

## 8. Rollback

Allowed rollback policies in v1:

- `NONE`;
- `BUILTIN_TRANSACTIONAL_V1`.

A built-in rollback is eligible only when the same reviewed rollback policy is present in the static RPi5 operation registry, queue envelope, and LIVE-AUTH payload. `NONE` forbids automatic rollback.

## 9. Receipts are not authority

A deployment receipt uses `rozkalns.deploy-receipt.v1`.

Receipts are public-safe evidence only. They:

- cannot authorize execution;
- cannot extend TTL;
- cannot make a consumed request reusable;
- cannot cause automatic retry;
- cannot repair a failed result by repeating deployment.

The P2 RPi5 transport deliberately has no GitHub result writer. If a writer is added later, it must be a separately reviewed non-authority capability and must not give the authorization reader write access to LIVE-AUTH.

## 10. GitHub-side enforcement boundary

This repository may provide:

- source schemas;
- deterministic lint tooling;
- read-only issue-event linting;
- public-safe templates;
- policy documentation.

It must not contain RPi5 credentials, private keys, root helpers, production deploy implementations, arbitrary remote execution, or a workflow whose deterministic side effect executes production because a LIVE-AUTH issue exists.

The issue-event lint workflow uses only read permissions. Its failure or success is diagnostic evidence; the future RPi5 validator must independently enforce the full protocol.

## 11. Source contract ownership

The RPi5 executor implementation and durable replay state remain owned by `rozkalnsandris/RPi5_main`.

Cross-repository compatibility between this GitHub-side contract and the RPi5 parser/transport is explicitly audited again in P5 before any host activation.
