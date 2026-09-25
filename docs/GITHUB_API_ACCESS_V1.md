# GitHub API Access v1

Status: ACTIVE shared governance contract  
Canonical repository: `rozkalnsandris/ops-workflows`  
Tracking: `ops-workflows#108`, contract slice `#109`, read-plan slice `#110`

## Purpose

Define one deterministic GitHub API access discipline for `START`, `SYNC`, `turpini`, AUTO-RUN FULL PR convergence, CI/review refresh, final pre-merge refresh, and exact-main reconciliation.

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
11. Do not rotate tokens, accounts, IPs, or endpoints to evade quota enforcement.
12. Repository-local stricter rules always win.

## Request-budget classes

These classes are qualitative control surfaces, not brittle fixed request counts.

### `BOOTSTRAP_MINIMAL`

Used by normal `START <repo>`.

Retrieve only enough to identify one canonical current lane:

- repository-local rules;
- canonical handoff/continuation when present;
- current default-branch SHA;
- current issue/PR identity needed for the selected lane.

Do not enumerate unrelated issues, PRs, workflow history, comments, or files by default.

### `PR_REFRESH_COMPACT`

Used while converging one active PR.

Refresh only mutable evidence required for the current PR decision, normally:

- exact PR head;
- required checks/status;
- reviews;
- unresolved review threads;
- mergeability/base state only when relevant to the current decision.

Changed-file enumeration is on-demand, not part of every refresh.

### `FINAL_PREMERGE_COMPACT`

Used immediately before an already-authorized merge/write.

Refresh only operation-binding facts such as current main/base, exact head, mergeability, required exact-head CI, reviews, unresolved threads, and exact authority binding.

This is not a repository-wide audit.

### `EXACT_MAIN_MINIMAL`

Used after a confirmed merge/write when repository policy requires reconciliation.

Retrieve only the resulting current `main` identity and the minimum exact-main evidence required by repository rules. Broaden only if reconciliation fails or exposes drift.

### `PR_FILES_ON_DEMAND`

List/fetch changed files only when the current issue, diff review, test failure, or review thread requires file-level evidence.

Do not repeatedly enumerate unchanged file lists during CI/review refresh.

### `DEEP_AUDIT_EXPLICIT`

Broader retrieval is permitted only under an explicit audit mode such as `AUDIT-HANDOFF` or when a concrete failure/conflict requires deeper evidence. Even then, avoid duplicate reads and bound pagination.

## Compact PR read plans

The budget classes above map to explicit lane plans. These plans define the default read surface; a concrete failure, review finding, conflict, or repository-local stricter rule may require demand-driven expansion.

### Normal `START <repo>` when the selected lane is a PR

After repository routing identifies the current PR, retrieve only the evidence needed to understand its current gate:

```text
repository rules / canonical continuation when needed
current main SHA
current issue / PR identity
exact PR head
required checks or status
reviews
unresolved review threads
```

Do not fetch by default:

```text
unrelated issues or PRs
historical workflow runs
all changed files
all comments
all commits
repo-wide inventory
```

The PR identity/head and CI/review evidence may come from one aggregate connector operation when that operation returns the same required canonical facts. Do not split one sufficient response into several narrower duplicate reads merely for presentation convenience.

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

Already-returned evidence may be reused inside the same bounded decision step while its identity is still exact. A later user continuation, event wakeup, head change, check completion, review change, or other meaningful state transition requires the appropriate fresh canonical refresh.

### File-level inspection

Changed-file evidence is a separate on-demand lane:

1. enumerate changed filenames only when file-level evidence is actually required;
2. use one API-provided paginated listing for a stable PR head when that listing is sufficient;
3. fetch patches only for the specific files that require inspection;
4. do not re-fetch the unchanged file list during ordinary CI/review refresh.

A PR existing is not itself a reason to enumerate every changed file.

### CI/review refresh

CI/review continuation is event/state driven by default:

```text
check/review state change, webhook/task wakeup, meaningful delay, or user continuation
-> refresh exact-head checks/reviews/threads
-> continue the same lane
```

Do not tight-loop on unchanged checks. Do not fetch unrelated historical workflow runs merely to determine the current exact-head state.

When the connector exposes an aggregate typed operation that already returns the required exact-head evidence, prefer it over multiple calls that duplicate the same facts. When no such operation exists, use the smallest serial sequence that proves the gate.

### Explicit deep audit

`AUDIT-HANDOFF` and other explicit repo-wide audits remain valid. They are not normal `START`/`SYNC` behavior and must be visibly treated as `DEEP_AUDIT_EXPLICIT`.

Even an explicit audit must avoid duplicate reads, honor API pagination, and stop expanding once the requested audit question has sufficient evidence.

## Connector capability honesty

The contract describes preferred primitives, not fictional capabilities.

- If a connector exposes `ETag`, `Last-Modified`, `If-None-Match`, or `If-Modified-Since`, use them where useful.
- If it does not expose those headers, fall back to minimum-sufficient/event-driven retrieval; do not claim conditional caching occurred.
- If GraphQL is unavailable, use bounded REST/typed connector operations; do not add a second transport solely to satisfy this contract.
- If an aggregate typed connector operation returns equivalent canonical evidence, prefer it over custom GraphQL or several narrower duplicate calls.
- Connector capability limitations never justify broader retrieval or weaker authority checks.

## Event-driven continuation

Preferred model:

```text
GitHub event / user continuation / meaningful state transition
-> fresh minimum-sufficient canonical refresh
-> continue current lane
```

Avoid:

```text
tight timer
-> same PR/check reads
-> same reads again
-> repeated unchanged polling burst
```

Webhook/event payloads are wake signals, not authority and not canonical state. A wakeup must still refresh the necessary GitHub facts before acting.

## Rate-limit evidence classification

Use the following stable dispositions when the relevant evidence is available:

- `PRIMARY_RATE_LIMIT_EXHAUSTED` — GitHub reports primary quota exhaustion, including `x-ratelimit-remaining: 0`.
- `SECONDARY_RATE_LIMIT_SUSPECTED` — a `403`/`429` or documented secondary-limit response occurs without proof of primary exhaustion.
- `RETRY_AFTER_REQUIRED` — a `Retry-After` value is present and defines the earliest safe read retry.
- `RESET_WAIT_REQUIRED` — primary remaining is zero and `x-ratelimit-reset` defines the earliest safe read retry.
- `READ_BACKOFF_REQUIRED` — secondary-limit handling requires a delay/backoff before another read attempt.
- `TRANSPORT_RATE_LIMIT_METADATA_UNAVAILABLE` — the connector/transport reports rate limiting but does not expose the relevant headers; do not invent values.

GitHub does not expose a direct authoritative query for current secondary-limit state. Never claim exact secondary-limit remaining capacity when it is not provided.

## Read-path interruption

A rate-limit/backoff disposition may pause or stop a read path before the desired audit is complete. That is a normal fail-closed outcome, not permission to fan out through alternate endpoints.

A read-path interruption must not:

- widen source, merge, LIVE, deploy, retry, rollback, cleanup, secrets, permission, or settings authority;
- trigger an unrelated repo-wide scan merely to find equivalent evidence;
- switch accounts/tokens/endpoints to bypass enforcement.

Resume only under the applicable bounded read backoff and fresh canonical-state rules.

## Pre-mutation read-only backoff

These retry rules apply only before the first authorized mutation starts.

1. If `Retry-After` is present, do not retry before that interval.
2. Else if `x-ratelimit-remaining == 0`, do not retry before `x-ratelimit-reset`.
3. Else for a secondary-limit response, wait at least 60 seconds before retrying.
4. Repeated secondary-limit responses use bounded exponential backoff.
5. The retry budget must remain compatible with a repository-local stricter technical-attempt limit; in this fleet, a `3 failed attempts -> STOP` rule may be stricter and therefore wins.
6. No busy loop, parallel alternate-endpoint probing, or quota-evasion behavior.

A read retry never creates merge/write/LIVE authority.

## Mutation boundary

This v1 access contract distinguishes read retry from mutation retry authority.

Once an authorized mutation is dispatched/started:

- authorization consumption is governed by repository-local policy;
- a `403`, `429`, timeout, transport failure, malformed response, or uncertain completion state must not trigger an automatic duplicate mutation;
- gather only the minimum permitted read-only evidence needed to preserve/reconcile state;
- STOP when the repository's fail-closed rule requires it;
- any later retry of the mutation requires authority from the applicable repository contract.

Detailed mutation-outcome reason codes and reconciliation are implemented by follow-up slice `ops-workflows#111`; this contract already forbids rate-limit handling from creating implicit mutation retry authority.

## GraphQL and REST bounds

GraphQL is an optimization, not a requirement.

Use it only when the available integration can reduce call count without hiding important state boundaries. Request only required fields, use cursor pagination, keep every connection `first`/`last` within 1–100, and avoid giant deeply nested PR/files/comments/reviews/checks queries.

When typed connector operations already aggregate the required evidence, prefer them rather than adding a second custom GraphQL layer without a demonstrated benefit.

REST list operations must follow returned pagination links/cursors or equivalent API-provided pagination semantics and stop when the current lane has sufficient evidence.

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
