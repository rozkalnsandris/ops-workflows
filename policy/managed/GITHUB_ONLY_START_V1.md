## GITHUB-ONLY / LIVE-ALL v1 — managed adoption block

Shared contract:
`rozkalnsandris/ops-workflows/docs/GITHUB_ONLY_LIVE_ALL.md`

Startup contract:
`rozkalnsandris/ops-workflows/docs/START_GITHUB_ONLY_V1.md`

Machine policy:
`rozkalnsandris/ops-workflows/policy/github-only-live-all-v1.json`

Repository manifest:
`.github/start-github-only.json`

### Activation boundary

When GITHUB-ONLY is inactive, plain `START <repository>` MUST NOT activate it.

Activation requires an explicit current command:

```text
GITHUB-ONLY
git hub only
START <repository> GITHUB-ONLY
START <repository> git hub only
```

Do not infer activation from the presence of this managed block, the repository manifest, policy adoption, or prior unrelated chat state.

If GITHUB-ONLY is already active in the same session, its existing persistence rule remains unchanged until `LIVE-ALL` completes/stops or the owner explicitly cancels the mode.

### Deterministic START bootstrap

`START <repository> GITHUB-ONLY` MUST refresh canonical GitHub state in this order:

1. local `AGENTS.md`, path-scoped governing rules, and repository-local handoff/master state;
2. shared GITHUB-ONLY / LIVE-ALL policy, START contract, machine policy, and adoption manifest;
3. current default-branch identity and governance capability;
4. active PRs with exact head/base/CI/review evidence;
5. active issues, roadmap/handoff and declared dependencies;
6. relevant central deploy-queue items;
7. the highest-priority canonical safe continuation using manifest precedence/tie-break rules;
8. bounded GitHub/source work with just-in-time revalidation before state-dependent writes;
9. final routing to `READY_FOR_MERGE`, `PARKED`, `STOP_ERROR`, `NEW_SCOPE_OR_RISK`, `AMBIGUOUS_CANONICAL_LANE`, or `IDLE`.

The absence of an open issue alone is NOT a STOP condition.
Do not invent speculative work when no canonical continuation exists.
If two equally authoritative lanes remain after declared tie-breakers, report `AMBIGUOUS_CANONICAL_LANE` instead of choosing arbitrarily.
If no canonical safe lane exists, report `IDLE`.

### Deferred live state

`PARKED` is a session/reporting state, never a deploy-queue title state.

Executor unavailability alone MUST NOT change a READY queue item to BLOCKED. Report:

```text
PARKED / EXECUTOR_UNAVAILABLE
Queue remains READY.
NO ACTION REQUIRED NOW.
```

Use BLOCKED only when deploy eligibility or another contract invariant actually fails.

Repository-local stricter safety and trust-boundary rules remain authoritative.
