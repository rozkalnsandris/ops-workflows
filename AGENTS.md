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
- Use one Ready receipt; refresh mutable state again immediately before merge.
- Composite Live authority must bind exact SHA/ref, exact target, allowed mutation categories, explicit exclusions, and baseline/operation limits where practical.
- Authorization is consumed when the first authorized mutation starts. After that, error, ambiguity, drift, or new risk means preserve evidence and STOP; do not automatically retry, rollback, clean up, rebase, reset, or choose an alternate mutation path unless that behavior was explicitly pre-authorized.
- When an owner decision remains, report status first and place one visible `ACTION REQUIRED` section at the end, using a copyable fenced `bash` block when practical.
- Merge remains explicit owner authority. Merge does not authorize deployment or any other live mutation.

Repository-local stricter rules in consuming projects override this shared baseline.

## Scope boundary

Keep this repository GitHub-side and reusable. Do not place RPi5 credentials, root helpers, production deploy implementations, database apply logic, private keys, or arbitrary remote-execution bridges here.

Shared workflows must be fail-closed, least-privilege, deterministic, and safe for their documented repository visibility. Consumers should pin reusable workflows to immutable commit SHAs after review/canary acceptance.
