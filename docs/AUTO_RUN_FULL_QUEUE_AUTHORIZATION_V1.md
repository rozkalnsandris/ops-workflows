# AUTO-RUN FULL Queue batch authorization v1

**Status:** A3 shared batch-authorization source contract; not active in consumers  
**Canonical repository:** `rozkalnsandris/ops-workflows`  
**Tracking issue:** `#39`  
**Parent design:** `docs/AUTO_RUN_FULL_QUEUE_V1.md`  
**Controller state:** `docs/AUTO_RUN_FULL_QUEUE_CONTROLLER_V1.md`

## 1. Purpose

A3 defines the intended authority semantics for one future AUTO-RUN FULL Queue activation.

The target owner command is:

```text
AUTO-RUN FULL QUEUE <owner/repo> #<issue1> #<issue2> ... #<issueN>
```

with:

```text
1 <= N <= 10
```

After a consumer explicitly adopts this completed shared contract, one fresh owner command may grant **source + merge authority for the exact frozen issue set**. The authority is sequential: only the currently ACTIVE item may use it.

A3 does not activate this command in any repository. Existing repository-local AUTO-RUN FULL remains authoritative until explicit consumer adoption.

Queue authority is never LIVE authority.

## 2. Why a durable authorization surface is required

Chat history and a controller cursor are not durable authority.

Before the first source mutation, a future adopted controller must materialize the owner decision into one consumer-repository batch/controller issue containing exactly one machine-readable authorization block.

The controller issue is not a work-item checklist. It is the immutable batch authorization receipt and continuation anchor.

The actual work remains in separate GitHub issues and PRs.

Progress belongs in comments and child issue/PR state. The authorization body must not be edited after creation.

If the authorization body is edited, the queue must fail closed with:

```text
STOP_AUTHORITY_INVALID
```

## 3. Authorization surface

Recommended controller issue title form:

```text
[AUTO-FULL-QUEUE][ACTIVE] <queue-id>
```

The exact consumer title convention may be stricter, but the body must contain one payload conforming to:

`policy/schemas/auto-run-full-queue-authorization-v1.schema.json`

Schema identity:

```text
rozkalns.auto-run-full-queue-auth.v1
```

Required bindings include:

- immutable `queue_id`;
- exact repository and stable repository ID;
- configured owner user ID;
- exact immutable `ops-workflows` shared-contract SHA adopted by the consumer;
- exact consumer `main` SHA at activation;
- SHA-256 digest of the consumer rules surface used at activation;
- ordered frozen issue list;
- stable issue node identity;
- per-issue scope digest;
- explicit authority flags: source = true, merge = true, LIVE = false.

## 4. Frozen issue scope

Each issue authority is frozen from canonical JSON equivalent to:

```json
{
  "repository": "owner/repo",
  "issue_number": 123,
  "title": "exact current title",
  "body": "exact current body"
}
```

The SHA-256 digest of that canonical representation becomes `scope_digest_sha256`.

The digest protects against later silent scope expansion.

Comments, labels and assignees are not themselves scope authority. They may provide evidence or workflow metadata, but they cannot silently widen the frozen Definition of Done.

If a later comment or edit materially changes required work, risk or trust boundary, the controller must STOP rather than reinterpret the original owner authorization.

## 5. What one adopted Queue activation authorizes

For every issue named in the frozen ordered list, the future adopted command may pre-authorize the normal source/merge cycle:

```text
fresh item state
-> task branch
-> source/docs/tests
-> focused validation
-> push
-> Draft PR
-> CI/review
-> bounded scope-preserving corrections allowed by local policy
-> Ready
-> fresh exact-head/rules/scope revalidation
-> squash merge using expected_head_sha
-> exact-main read-only verification
-> controller advance
```

No separate owner `MERGE` command is required for each queued issue once Queue mode is explicitly adopted and the batch authority is valid.

This is the deliberate vNext trust-boundary change from legacy issue-scoped AUTO-RUN FULL.

The authority for future items remains dormant until that exact issue becomes ACTIVE. It may not be used to create parallel writers or merge future items out of order.

## 6. Merge conditions remain strict

Batch merge authority does not mean unconditional merge.

Immediately before each merge, the controller must freshly prove at least:

- the same issue is still ACTIVE;
- the issue number/node identity and scope digest still match the frozen receipt;
- consumer rules still match the frozen/accepted authority boundary or are otherwise explicitly proven compatible;
- exact PR head is known;
- required exact-head CI is PASS;
- required review state and unresolved-thread rules pass;
- PR is mergeable under repository-local policy;
- no conflicting queue/PR authority exists;
- the merge call binds `expected_head_sha`.

If any required fact changes, do not reinterpret the owner decision. STOP or revalidate only as allowed by the existing source policy.

## 7. Main stability barriers

After the batch/controller authorization issue is created, re-read consumer `main` before the first source mutation.

The first item may start only when:

```text
current_main == activation_main_sha
```

After that, `main` is expected to advance through successfully completed queue items.

Before activating the next issue, the controller must freshly prove the exact-main result of the prior item. Unexpected external `main` drift that is not explained by the proven queue chain requires STOP.

This prevents a queue activation from silently attaching itself to a materially different repository state.

## 8. Rules stability

The receipt binds the consumer rules surface used to make the batch decision, represented by `consumer_rules_digest_sha256`.

Before each item activation and immediately before merge, the controller must freshly read applicable repository rules.

A material rules/trust-boundary change is not absorbed automatically by an older Queue authorization.

If one queued issue intentionally changes the governing rules, subsequent dormant issue authority must STOP for a new owner decision unless the active reviewed contract explicitly proves that the change does not alter the authorization boundary.

Default behavior is fail closed.

## 9. Stop conditions

The queue must stop without skipping when any of these occur:

- issue title/body scope digest changes;
- issue identity/repository mismatch;
- governing rules or trust boundary materially change;
- dependency order becomes ambiguous;
- another active queue or conflicting authority appears;
- an unexpected external `main` change breaks the proven chain;
- a required review/CI/merge fact cannot be proven;
- source corrections exceed repository-local attempt limits;
- the current item introduces a new mutation/risk class outside the frozen source authority.

A blocked/failed current issue must not be skipped simply to keep throughput high.

Changing the frozen issue order, inserting another issue or replacing an item requires a new owner Queue activation.

## 10. What Queue authority never includes

The batch command does not authorize:

- production deploy or runtime mutation;
- Cloudflare Worker/D1/Queue mutation;
- secrets, credentials or tokens;
- repository settings, permissions or branch-protection mutation;
- RPi5 host/root/systemd/Docker/network mutation;
- database apply/migration;
- destructive cleanup;
- undeclared retry/rollback/alternate mutation path;
- work outside the exact frozen issue scopes.

Merge never implies any of those authorities.

## 11. Queue completion and LIVE

After the final frozen issue has merged and exact-main evidence is proven:

```text
QUEUE_SOURCE_COMPLETE
-> final exact-main + required exact-SHA CI
-> GET/SELECT/read-only reconciliation
```

Then:

```text
no live mutation required -> DONE
live mutation required    -> PAUSED_OWNER_LIVE_GATE
```

The final LIVE decision is separate from the Queue activation and binds the exact final SHA/target/fixed reviewed rollout under the later Simple LIVE contract.

## 12. Compatibility and adoption

A3 is still source-policy-only shared work.

Until a consumer explicitly adopts a completed Queue contract pinned to an immutable `ops-workflows` SHA:

- `AUTO-RUN FULL QUEUE ...` is not an active command;
- a batch/controller issue is not queue-wide source/merge authority;
- legacy repository-local AUTO-RUN FULL remains authoritative;
- normal explicit merge gates remain unchanged;
- no consumer is migrated by inference.

The later adoption PR must explicitly reconcile repository-local rules and identify the controller/authorization surface before Queue mode becomes active there.

## 13. A3 acceptance

A3 is complete when shared policy/tests prove:

- exact owner command cannot be inferred;
- queue size is 1–10 ordered unique issues;
- one adopted activation grants source+merge only for the frozen items;
- only one item may consume that authority at a time;
- durable GitHub receipt is required before first source mutation;
- receipt body is immutable after creation;
- issue scope and repository rules are frozen and revalidated;
- exact-head merge requirements remain intact;
- scope/rules/main drift fails closed;
- queue never grants LIVE;
- A3 itself activates no consumer.
