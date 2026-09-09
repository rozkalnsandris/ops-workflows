# AUTO-RUN FULL Queue controller state v1

**Status:** A2 shared controller-state source contract; not active in consumers  
**Canonical repository:** `rozkalnsandris/ops-workflows`  
**Tracking issue:** `#39`  
**Parent contract:** `docs/AUTO_RUN_FULL_QUEUE_V1.md`

## 1. Purpose

A2 defines the smallest deterministic controller state needed to move through a frozen AUTO-RUN FULL Queue without turning the controller into a second copy of GitHub issue/PR/CI state.

The controller records only:

- repository;
- immutable queue identity;
- frozen ordered issue numbers;
- cursor;
- coarse queue state;
- current active issue when one exists;
- per-item coarse state;
- exact source-terminal evidence for completed items.

GitHub remains canonical for the underlying issue, PR, review, CI and merge facts.

A2 is source-only. It does not activate a Queue command, grant batch source/merge authority, migrate a consumer or authorize LIVE.

## 2. Snapshot schema

Canonical schema:

`policy/schemas/auto-run-full-queue-controller-state-v1.schema.json`

Schema identifier:

`rozkalns.auto-run-full-queue-controller-state.v1`

Initial queue size remains:

```text
1 <= frozen_issues <= 10
```

Issue numbers must be positive, unique and preserve the exact activation order.

## 3. Queue states

The shared controller uses five queue states:

```text
READY
ACTIVE
PAUSED
QUEUE_SOURCE_COMPLETE
STOPPED
```

Per-item state is limited to:

```text
PENDING
ACTIVE
SOURCE_COMPLETE
STOPPED
```

There is never more than one ACTIVE item.

### READY

- cursor is `0`;
- `active_issue` is null;
- every item is `PENDING`.

### ACTIVE

- cursor points inside the frozen queue;
- `active_issue == frozen_issues[cursor]`;
- every prior item is `SOURCE_COMPLETE`;
- current item is `ACTIVE`;
- every later item is `PENDING`.

### PAUSED

PAUSED preserves the same cursor and active issue as ACTIVE. It is a continuation state, not an authorization state.

### QUEUE_SOURCE_COMPLETE

- cursor equals queue length;
- `active_issue` is null;
- every item is `SOURCE_COMPLETE`.

This is source completion only. It does not imply LIVE authorization.

### STOPPED

- cursor remains on the stopped issue;
- previous items remain `SOURCE_COMPLETE`;
- current item is `STOPPED`;
- later items remain `PENDING`;
- no automatic resume or skip occurs.

## 4. Source-terminal evidence

The controller may advance only after the current issue has exact source-terminal evidence:

```json
{
  "pr_number": 123,
  "merged_head_sha": "0123456789abcdef0123456789abcdef01234567",
  "exact_main_sha": "89abcdef0123456789abcdef0123456789abcdef",
  "exact_main_ci": "PASS"
}
```

Requirements:

- `pr_number` is positive;
- both SHAs are lowercase exact 40-hex identities;
- exact-main CI must equal `PASS`;
- evidence exists only on `SOURCE_COMPLETE` items.

Evidence proves transition eligibility; it is not source, merge or LIVE authority.

## 5. Deterministic transitions

Allowed controller transitions are intentionally narrow.

```text
READY --activate--> ACTIVE(first issue)

ACTIVE --source complete evidence--> ACTIVE(next issue)
ACTIVE --final source complete evidence--> QUEUE_SOURCE_COMPLETE

ACTIVE --pause--> PAUSED
PAUSED --resume--> ACTIVE(same issue)

ACTIVE|PAUSED --stop--> STOPPED(same issue)
```

The controller must not:

- skip a pending issue;
- reorder frozen issues;
- insert a future issue;
- advance without source-terminal evidence;
- auto-resume a STOPPED queue;
- reinterpret PAUSED/STOPPED as a new authorization.

The next active issue is always the issue at `cursor + 1` in the original frozen order.

## 6. Validation implementation

Shared validator:

`scripts/validate_auto_run_full_queue_state.py`

The validator is read-only and pure with respect to GitHub/production state. It validates snapshots and exposes deterministic helper transitions for tests/source reuse:

- `make_ready`;
- `activate`;
- `advance_after_source_complete`;
- `pause`;
- `resume`;
- `stop`.

It does not call GitHub, merge PRs, mutate issues, deploy or access credentials.

## 7. Test requirements

Canonical tests:

`tests/auto_run_full_queue/test_controller_state.py`

The suite must prove at minimum:

- valid READY snapshot;
- first-item activation;
- exactly-one-item advance;
- final source completion;
- pause/resume preserves cursor and active issue;
- STOP does not advance;
- duplicate/reordered scope fails closed;
- two ACTIVE items fail closed;
- cursor skip attempts fail closed;
- missing/invalid exact-main evidence blocks advance;
- STOPPED cannot auto-resume/advance;
- schema and validator surfaces remain aligned;
- A1/A2 remain source-only and non-authoritative.

## 8. Canonical-state boundary

The controller snapshot is a compact continuation projection, not canonical truth for mutable GitHub facts.

Before source work, merge or any later LIVE step, the consuming controller must freshly retrieve the repository-local canonical facts required by that action.

Chat history, memory, runner queue order and stale controller evidence must never override fresh GitHub state.

## 9. Compatibility boundary

A2 preserves A1 compatibility:

- Queue command remains inactive;
- no consumer auto-migration;
- old AUTO-RUN FULL remains authoritative until explicit per-consumer adoption;
- no queue-wide source authority;
- no queue-wide merge authority;
- no LIVE authority;
- `ops-workflows` remains GitHub-side policy/guard infrastructure only.

The next design slice after A2 is explicit batch authorization semantics. That future slice must decide exactly what one Queue activation may authorize for the frozen issue set before any consumer can use Queue mode.
