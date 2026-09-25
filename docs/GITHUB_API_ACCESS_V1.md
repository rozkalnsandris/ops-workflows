# GitHub API Access v1

Status: ACTIVE shared governance contract  
Canonical repository: `rozkalnsandris/ops-workflows`  
Tracking: `ops-workflows#108`, contract slice `#109`, read-plan slice `#110`, mutation-boundary slice `#111`

## Purpose

Define one deterministic GitHub API access discipline for `START`, `SYNC`, `turpini`, AUTO-RUN FULL PR convergence, CI/review refresh, final pre-merge refresh, mutation dispatch, and exact-main reconciliation.

The goal is to reduce primary/secondary rate-limit pressure without weakening canonical-state freshness, exact-head checks, owner gates, authorization consumption, or fail-closed behavior.

This contract governs access behavior. It does not grant source, merge, LIVE, deployment, secrets, permission, settings, or production-data authority.

## Authoritative GitHub references

Implementation must remain aligned with current GitHub documentation:

- REST best practices: <https://docs.github.com/en/rest/using-the-rest-api/best-practices-for-using-the-rest-api>
- REST rate limits: <https://docs.github.com/en/rest/using-the-rest-api/rate-limits-for-the-rest-api>
- REST troubleshooting: <https://docs.github.com/en/rest/using-the-rest-api/troubleshooting-the-rest-api>
- GraphQL rate/query limits: <https://docs.github.com/en/graphql/overview/rate-limits-and-query-limits-for-the-graphql-api>
- GraphQL pagination: <https://docs.github.com/en/graphql/guides/using-pagination-in-the-graphql-api>
- Webhooks: <https://docs.github.com/en/webhooks/about-webhooks>

When GitHub changes documented limits or retry semantics, fresh GitHub documentation wins over historical numeric values recorded elsewhere.

## Core rules

1. Prefer authenticated GitHub access whenever the available integration supports it.
2. Execute one repository lane serially by default. Do not create broad parallel request fan-out merely to make an audit faster.
3. Retrieve only the minimum canonical facts required for the current lane or gate.
4. Reuse already-returned evidence inside the same bounded decision step instead of immediately fetching the same state again.
5. Prefer event/state-driven continuation over tight polling.
6. When polling is unavoidable, use the lowest useful frequency and honor `x-poll-interval` when the transport exposes it.
7. Use authenticated conditional requests (`ETag`/`If-None-Match` or `Last-Modified`/`If-Modified-Since`) when the transport exposes those primitives. Do not pretend the capability exists when the connector does not expose it.
8. Use API-provided pagination semantics and explicit bounds. Never implement unbounded scans as part of a normal work-cycle refresh.
9. GraphQL consolidation is allowed only when it reduces total request cost and stays bounded. Every connection must use `first` or `last` in the range 1–100 and queries must remain comfortably below GitHub's documented 500,000-node limit.
10. Do not continuously poll `/rate_limit`; response headers and the triggering error are the preferred live evidence when available.
11. Do not rotate tokens, accounts, IPs, endpoints, or tools to evade quota enforcement.
12. Repository-local stricter rules always win.

## Request-budget classes

These classes are qualitative control surfaces, not brittle fixed request counts.

### `BOOTSTRAP_MINIMAL`

Used by normal `START <repo>`. Retrieve only enough to identify one canonical current lane: repository-local rules, canonical handoff/continuation when present, current default-branch SHA, and the current issue/PR identity required by that lane. Do not enumerate unrelated issues, PRs, workflow history, comments, files, or commits by default.

### `PR_REFRESH_COMPACT`

Used while converging one active PR. Refresh only mutable evidence required for the current PR decision: exact PR head, required checks/status, reviews, unresolved review threads, and mergeability/base state only when relevant.

### `FINAL_PREMERGE_COMPACT`

Used immediately before an already-authorized merge/write. Refresh only operation-binding facts: current main/base, exact PR head, mergeability, required exact-head CI/status, reviews, unresolved threads, and exact authority binding. This is not a repository-wide audit.

### `EXACT_MAIN_MINIMAL`

Used after a confirmed merge/write or when reconciling a previously ambiguous mutation that fresh GitHub state proves succeeded. Retrieve only the resulting current `main` identity and minimum exact-main lineage/evidence required by repository rules.

### `PR_FILES_ON_DEMAND`

List/fetch changed files only when the current issue, diff review, test failure, or review thread requires file-level evidence. Do not repeatedly enumerate unchanged file lists during CI/review refresh.

### `DEEP_AUDIT_EXPLICIT`

Broader retrieval is permitted only under an explicit audit mode such as `AUDIT-HANDOFF` or when a concrete failure/conflict requires deeper evidence. Even then, avoid duplicate reads and bound pagination.

## Compact PR read plans

### Normal `START <repo>` when the selected lane is a PR

Retrieve only:

```text
repository rules / canonical continuation when needed
current main SHA
current issue / PR identity
exact PR head
required checks or status
reviews
unresolved review threads
```

Do not fetch by default unrelated issues/PRs, historical workflow runs, all changed files, all comments, all commits, or a repo-wide inventory.

When one aggregate connector operation already returns the same required canonical facts, prefer it over several narrower duplicate reads.

### Normal `SYNC <repo>` / `turpini` on an active PR

Refresh the selected lane only:

```text
current main when relevant to the gate
exact current PR head
required exact-head checks/status
reviews
unresolved review threads
```

Do not re-enumerate changed files, comments, commits, unrelated workflow history, or unrelated repository state unless the lane exposes a concrete reason to do so.

### File-level inspection

1. Enumerate changed filenames only when file-level evidence is actually required.
2. Use one API-provided paginated listing for a stable PR head when that listing is sufficient.
3. Fetch patches only for specific files that require inspection.
4. Do not re-fetch the unchanged file list during ordinary CI/review refresh.

### CI/review refresh

CI/review continuation is event/state/user-continuation driven by default. Do not tight-loop on unchanged checks and do not fetch unrelated historical workflow runs merely to determine current exact-head state.

### Explicit deep audit

`AUDIT-HANDOFF` and other explicit repo-wide audits remain valid but are not normal `START`/`SYNC` behavior. Even an explicit audit must avoid duplicate reads, honor API pagination, and stop expanding once the audit question has sufficient evidence.

## Connector capability honesty

- Use conditional request headers only when the connector exposes them.
- If GraphQL is unavailable, use bounded REST/typed connector operations.
- Prefer an aggregate typed connector operation when it already returns equivalent canonical evidence.
- Connector capability limitations never justify broader retrieval or weaker authority checks.

## Event-driven continuation

Preferred model:

```text
GitHub event / user continuation / meaningful state transition
-> fresh minimum-sufficient canonical refresh
-> continue current lane
```

Avoid tight timers that repeatedly read the same PR/check state. Webhook/event payloads are wake signals, not authority and not canonical state.

## Rate-limit evidence classification

Use these stable dispositions when supported by available evidence:

- `PRIMARY_RATE_LIMIT_EXHAUSTED` — GitHub reports primary quota exhaustion, including `x-ratelimit-remaining: 0`.
- `SECONDARY_RATE_LIMIT_SUSPECTED` — a `403`/`429` or documented secondary-limit response occurs without proof of primary exhaustion.
- `RETRY_AFTER_REQUIRED` — `Retry-After` defines the earliest safe read retry.
- `RESET_WAIT_REQUIRED` — primary remaining is zero and `x-ratelimit-reset` defines the earliest safe read retry.
- `READ_BACKOFF_REQUIRED` — secondary-limit handling requires delay/backoff before another read attempt.
- `TRANSPORT_RATE_LIMIT_METADATA_UNAVAILABLE` — the connector reports rate limiting but does not expose relevant headers; do not invent values.

GitHub does not expose a direct authoritative query for current secondary-limit capacity.

## Read-path interruption

A rate-limit/backoff disposition may pause or stop a read path before the desired audit is complete. It must not widen authority, trigger an unrelated repo-wide scan, or switch accounts/tokens/endpoints/tools to bypass enforcement.

## Pre-mutation read-only backoff

These retry rules apply only before the first authorized mutation starts:

1. If `Retry-After` is present, do not retry before that interval.
2. Else if `x-ratelimit-remaining == 0`, do not retry before `x-ratelimit-reset`.
3. Else for a secondary-limit response, wait at least 60 seconds before retrying.
4. Repeated secondary-limit responses use bounded exponential backoff.
5. Repository-local stricter attempt limits win; this fleet commonly uses `3 failed attempts -> STOP`.
6. No busy loop, parallel alternate-endpoint probing, or quota-evasion behavior.

A read retry never creates merge/write/LIVE authority.

## Final pre-mutation gate

Immediately before an already-authorized merge/write, perform one serial `FINAL_PREMERGE_COMPACT` refresh of only the mutable facts that bind the operation:

```text
current main/base
exact PR head
mergeability
required exact-head CI/status
reviews
unresolved review threads
exact owner/FULL authority binding
```

Do not perform a broad repository audit at this point. If the GitHub mutation operation supports an expected-head SHA, bind the mutation to the exact expected head. Head/base/authority drift rejects before dispatch rather than broadening or guessing.

## Mutation outcome dispositions

After mutation authority reaches the dispatch boundary, classify outcomes with these stable codes:

```text
MUTATION_CONFIRMED_SUCCESS
MUTATION_CONFIRMED_REJECTED_BEFORE_APPLY
MUTATION_OUTCOME_UNKNOWN_RATE_LIMIT
MUTATION_OUTCOME_UNKNOWN_TIMEOUT
MUTATION_OUTCOME_UNKNOWN_TRANSPORT
POST_MUTATION_RECONCILIATION_REQUIRED
```

`MUTATION_CONFIRMED_REJECTED_BEFORE_APPLY` is valid only when available evidence positively proves that the mutation was rejected before it could apply. A `429`, timeout, malformed/partial response, connector disconnect, or transport failure after dispatch does not prove that the server failed to apply the mutation.

## Mutation boundary

Once an authorized mutation call is dispatched/started:

- authorization is consumed according to repository-local policy;
- no automatic second merge/write call is permitted;
- `403`, `429`, timeout, transport disconnect, malformed/partial response, or uncertain completion is fail-closed unless evidence positively proves rejection before apply;
- `429` must never be interpreted as proof that the mutation did not apply;
- do not switch endpoints, tools, accounts, or tokens to try the mutation again;
- do not rollback, cleanup, rebase, reset, or choose an alternate mutation path merely to recover the lane;
- merge success never implies LIVE/deploy authority.

An ambiguous rate-limit response after dispatch is `MUTATION_OUTCOME_UNKNOWN_RATE_LIMIT`; timeout is `MUTATION_OUTCOME_UNKNOWN_TIMEOUT`; other transport uncertainty is `MUTATION_OUTCOME_UNKNOWN_TRANSPORT`. Each requires fail-closed reconciliation, not automatic retry.

## Post-mutation reconciliation

After ambiguity, the same run may gather only the minimum permitted read-only evidence needed to preserve state, normally current PR merged state and current `main`. It must still STOP and must not issue another mutation.

If rate limiting prevents even that minimum evidence, preserve what is already known and STOP without further probing.

The next `SYNC <repo>` or explicitly authorized continuation must freshly read canonical GitHub state:

- if the exact expected PR head is proven merged and resulting main lineage is correct, reconcile as `MUTATION_CONFIRMED_SUCCESS`; do not merge again;
- if fresh state proves the mutation did not occur, consumed authorization does not revive silently; a new explicit merge/write authority is required unless a repository-local contract had already pre-authorized a bounded retry;
- if state remains ambiguous or drifted, remain STOPPED.

After a clearly confirmed merge response, use only `EXACT_MAIN_MINIMAL`. Do not immediately launch a full PR/files/comments/check-history audit burst. Broaden only when exact-main verification fails or exposes drift.

## Deterministic mutation scenarios

The machine policy records synthetic acceptance scenarios rather than intentionally exhausting GitHub quotas:

- exact-head guarded success -> confirmed success, no duplicate mutation, then `EXACT_MAIN_MINIMAL`;
- head drift before dispatch -> rejected before apply, no mutation;
- primary rate limit before dispatch -> bounded read backoff may apply;
- `429` after dispatch -> unknown rate-limit outcome, no duplicate mutation;
- timeout after dispatch -> unknown timeout outcome, no duplicate mutation;
- transport error after dispatch -> unknown transport outcome, no duplicate mutation;
- next SYNC proves applied -> reconciled success, no second mutation;
- next SYNC proves not applied -> fresh authority required.

## GraphQL and REST bounds

GraphQL is an optimization, not a requirement. Use it only when available and lower-cost, request only required fields, use cursor pagination, keep every connection `first`/`last` within 1–100, and avoid giant nested queries. REST list operations must follow API-provided pagination and stop once the current lane has sufficient evidence.

## Compatibility and authority

This contract does not change:

- GitHub as canonical mutable-state source;
- explicit MERGE by default;
- repository-local FULL-mode authority where separately activated;
- separation of merge from LIVE/deploy authority;
- first-mutation authorization consumption;
- fail-closed behavior after mutation uncertainty;
- repository-local stricter trust/security rules.

No consumer repository is silently migrated by merging this contract. Adoption/rollout is handled separately under `ops-workflows#112` after the shared contract and follow-up slices are proven.
