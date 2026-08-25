# Repository agent rules

This repository is the canonical shared GitHub-side automation and delivery-policy repository for `rozkalnsandris` projects.

## FAST-LANE v2.2 Composite

Before changing shared delivery policy, read all three canonical surfaces:

1. `docs/FAST_LANE_V2_1_HYBRID.md` — active normative FAST-LANE v2.2 policy; the v2.1 filename is retained only as a compatibility path for existing consumers.
2. `docs/FAST_LANE_V2_2_DECISION_RECORD.md` — migration rationale, operating history, anti-patterns, and the evidence explaining why v2.2 exists.
3. `policy/fast-lane-v2.2.json` — machine-readable invariants.

The core operating rule is:

**The human approves the RISK / DECISION. Automation executes the TECHNICAL STEPS.**

- `FAST` is source-only work through Ready; it never authorizes merge or live mutation.
- `STRICT` classifies live mutation risk. It does **not** imply one owner approval per technical checkpoint.
- The normal owner gate budget is at most two decisions: exact `MERGE`, then one bounded `COMPOSITE LIVE` only when a live mutation is actually required.
- CI polling, GET/preflight, evidence refresh, diff inspection, checkout discovery, clean/ancestor checks, build preparation, candidate verification, reconciliation, and other read-only steps do not create owner gates.
- A FAST PR may batch 2–5 closely related same-risk work items when they form one coherent acceptance story.
- Up to two scope-preserving corrective commits may follow CI/review findings inside the original FAST authorization. A third correction or scope/risk expansion requires STOP and new authorization.
- Three failed technical attempts for the same objective — the initial attempt plus at most two scope-preserving corrections — are a hard STOP before a fourth attempt.
- Use one Ready receipt; refresh mutable state again immediately before merge.
- Composite Live authority must bind exact SHA/ref, exact target, allowed mutation categories, explicit exclusions, and baseline/operation limits where practical.
- Candidate verification must prove that the observed candidate identity equals the exact uploaded artifact/version identity. HTTP success alone is insufficient when routing can fall back to another active version.
- When a platform requires a candidate to be attached to the active deployment before exact-version verification, a pre-enumerated zero-normal-traffic attachment plus later promotion may share one Composite Live owner gate. Both remain separate live mutations and must be counted and bounded in the authorization envelope.
- Authorization is consumed when the first authorized mutation starts. After that, error, ambiguity, drift, or new risk means preserve evidence and STOP; do not automatically retry, rollback, clean up, rebase, reset, or choose an alternate mutation path unless that behavior was explicitly pre-authorized.
- When an owner decision remains, report status first and place one visible `ACTION REQUIRED` section at the end, using a copyable fenced `bash` block when practical.
- Merge remains explicit owner authority. Merge does not authorize deployment or any other live mutation.

Repository-local stricter rules in consuming projects override this shared baseline.

## GITHUB-ONLY / LIVE-ALL v1

The canonical deferred-deployment operator mode is defined by:

1. `docs/GITHUB_ONLY_LIVE_ALL.md` — normative command, queue, snapshot, revalidation and failure semantics;
2. `docs/START_GITHUB_ONLY_V1.md` — deterministic `START <repo> GITHUB-ONLY` bootstrap, PARKED session UX, and executor-capability semantics;
3. `policy/github-only-live-all-v1.json` — machine-readable invariants;
4. `.github/ISSUE_TEMPLATE/deploy-queue.yml` — canonical public-safe deferred deploy queue issue form.

Operator rules:

- `GITHUB-ONLY` means perform GitHub/source-level work and prepare required live/deploy work up to, but not including, the first live mutation.
- `START <repo> GITHUB-ONLY` must refresh the full canonical continuation surface and select the next safe canonical lane; absence of an open issue alone is not a STOP condition.
- Persist deferred deploy work as `[DEPLOY-QUEUE]` GitHub Issues in this repository; never rely on chat or memory as the queue.
- Merge remains separately explicit. `GITHUB-ONLY` and `LIVE-ALL` never imply merge.
- A GitHub action whose deterministic side effect is a forbidden live mutation counts as live work and must not run under `GITHUB-ONLY`.
- Mark a queue item `READY` only after the final exact deployable SHA exists and no separate prerequisite owner gate remains.
- `PARKED` is a session/operator UX state, not a queue title state. A valid READY rollout remains READY when the current session lacks its declared executor.
- Executor availability is session capability, not rollout readiness. `READY + executor unavailable` means no live mutation, leave the issue READY, and report `PARKED / NO ACTION REQUIRED NOW`.
- `BLOCKED` is reserved for rollout eligibility or contract failure such as SHA/target/baseline/dependency/evidence/entrypoint/policy drift; executor unavailability alone is not BLOCKED.
- `LIVE-ALL` performs a read-only executor-capability check before freezing the executable READY snapshot; READY items that cannot run in the current session remain READY and are not selected.
- `LIVE-ALL` revalidates every selected exact SHA/target/baseline and executes only the predeclared ordinary deployment envelope.
- `LIVE-ALL` does not authorize database writes/migrations, secrets/credentials, permission/trust-boundary expansion, destructive cleanup, DNS/Tunnel/Access mutation or undeclared extra-risk work.
- After any live mutation starts, error or ambiguity requires public-safe evidence preservation and STOP of the remaining batch; no automatic retry/rollback/cleanup/alternate mutation path unless explicitly pre-authorized.
- Because this repository is public, queue issues must contain only public-safe operational metadata. Never place secrets or protected/private runtime data in them.

Repository-local stricter deployment and trust-boundary rules remain authoritative.

## Scope boundary

Keep this repository GitHub-side and reusable. Do not place RPi5 credentials, root helpers, production deploy implementations, database apply logic, private keys, or arbitrary remote-execution bridges here.

Shared workflows must be fail-closed, least-privilege, deterministic, and safe for their documented repository visibility. Consumers should pin reusable workflows to immutable commit SHAs after review/canary acceptance.
