# Repository agent rules

This repository is the canonical shared GitHub-side automation and delivery-policy repository for `rozkalnsandris` projects.

## FAST-LANE v2.1 Hybrid

Read `docs/FAST_LANE_V2_1_HYBRID.md` and `policy/fast-lane-v2.1.json` before changing shared delivery policy.

- `FAST` is source-only work through Ready; it never authorizes merge or live mutation.
- `STRICT` covers runtime authority, production, host/root, database writes/migrations, secrets, Cloudflare, firmware activation, physical actuation, and equivalent trust-boundary changes.
- A FAST PR may batch 2-5 closely related same-risk work items when they form one coherent acceptance story.
- Up to two scope-preserving corrective commits may follow CI/review findings inside the original FAST authorization. A third correction or scope/risk expansion requires STOP and new authorization.
- Use one Ready receipt; refresh mutable state again immediately before merge.
- Merge remains explicit owner authority. Merge does not authorize deployment or any other live mutation.

Repository-local stricter rules in consuming projects override this shared baseline.

## Scope boundary

Keep this repository GitHub-side and reusable. Do not place RPi5 credentials, root helpers, production deploy implementations, database apply logic, private keys, or arbitrary remote-execution bridges here.

Shared workflows must be fail-closed, least-privilege, deterministic, and safe for their documented repository visibility. Consumers should pin reusable workflows to immutable commit SHAs after review/canary acceptance.
