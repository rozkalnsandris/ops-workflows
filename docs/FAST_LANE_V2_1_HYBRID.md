# FAST-LANE v2.2 Composite — canonical cross-project policy

> Compatibility path: this file keeps the v2.1 filename because adopting repositories already point here. Its contents are the authoritative FAST-LANE v2.2 policy.
>
> **Why v2.2 exists:** read `docs/FAST_LANE_V2_2_DECISION_RECORD.md` for the migration rationale, Control Center evidence, rejected micro-gate model, 2026-08-22 rollout history, and external platform alignment.

## Core rule

**The human approves the RISK / DECISION. Automation executes the TECHNICAL STEPS.**

STRICT describes mutation risk, not the number of human interactions. Read-only checkpoints MUST NOT create owner gates.

Repository-local stricter trust-boundary rules still win.

## FAST source envelope

For source-only work, `START`, `turpini`, or an equivalent continuation instruction may proceed in one coherent batch from fresh canonical GitHub state through Ready:

`fresh state -> branch -> implementation -> focused validation -> push -> Draft PR -> CI/review -> up to 2 scope-preserving corrections -> Ready receipt -> STOP for merge`

FAST may batch 2-5 closely related same-risk work items when they form one reviewable acceptance story. FAST never authorizes merge or a live mutation.

## Human gate budget

The normal end-to-end delivery path has at most two owner decision gates:

1. **MERGE** — explicit authorization to merge the exact Ready PR/head.
2. **COMPOSITE LIVE** — only when a deploy/host/device/account/data mutation is actually required.

Do not invent separate owner gates for CI polling, GET/preflight, evidence refresh, diff inspection, checkout discovery, clean/ancestor checks, build preparation, candidate verification, reconciliation, or other read-only work.

A new STOP is justified only when:

- merge authorization is required;
- one composite live authorization is required;
- an authorized mutation has started and an error/ambiguous result occurs;
- a new scope, trust-boundary, target, SHA, or risk class appears.

## Composite STRICT authorization envelope

Before requesting a live authorization, collect all obtainable read-only evidence. Ask once for one bounded execution envelope that states:

- repository and exact approved Git SHA/ref;
- exact live target/environment/device/account;
- allowed mutation categories;
- hard mutation-count or operation limits where practical;
- explicit exclusions;
- expected pre-mutation production/runtime baseline when relevant.

One authorization may cover multiple tightly coupled mutation categories needed for one rollout, for example a trusted local checkout `git fetch` + `git merge --ff-only` followed by one bounded production rollout. It does not authorize `reset`, `rebase`, `clean`, force operations, secrets, permissions, unrelated host changes, DB/Queue mutations, or any category not named in the envelope.

If the approved SHA/target/baseline changes before the mutation, fail closed and STOP. Never silently deploy a newer `main` than the owner approved.

## One-shot execution

After Composite Live authorization, automation should execute one fail-closed controller/script rather than returning to the owner for technical checkpoints.

The one-shot sequence should include, as applicable:

1. exact GitHub/main/CI evidence;
2. production/runtime baseline read;
3. local checkout clean/ancestor validation;
4. allowed `fetch` + `merge --ff-only` sync when required;
5. revalidation of approved SHA and baseline immediately before first live write;
6. deterministic build with project-pinned toolchain;
7. build once / upload or create one exact artifact/version;
8. automated candidate/read-only verification;
9. concurrency/drift guard immediately before rollout;
10. one bounded rollout of the exact verified artifact/version;
11. GET/read-only reconciliation;
12. one final receipt.

When the platform supports immutable versions/artifacts, deploy the exact verified version; do not rebuild between candidate verification and rollout.

## Failure and rollback

Authorization is consumed when the first authorized mutation starts. After that point, any error, ambiguity, unexpected drift, or scope expansion requires evidence preservation and STOP.

Default behavior is **no automatic retry, rollback, cleanup, alternate mutation path, reset, or rebase**. Such behavior is allowed only when the exact operation contract explicitly pre-authorized it and its safety prerequisites were proven before the first mutation.

## Concurrency and drift

Only one bounded live rollout should own a target at a time. Immediately before a live write, re-read the expected authoritative baseline when the platform exposes it. If another actor changed the target, STOP instead of adapting automatically.

## Toolchain determinism

Production/release tooling must be repository-pinned or otherwise exact-version controlled where practical. Do not fetch an unpinned latest deployment CLI during the live rollout.

## Evidence

Use one Ready receipt for source work and one final live receipt after a Composite Live execution. Do not ask the owner to shuttle intermediate command output unless execution has genuinely stopped.

A live receipt should record at least:

- result and failed stage if any;
- approved and observed Git SHA;
- target and before/after baseline/version;
- allowed mutations and actual mutation counts;
- candidate verification and reconciliation result;
- whether first mutation started / authorization was consumed;
- whether production/runtime changed;
- exact next human decision, if one exists.

## Operator UX

Human decisions must be visually separated at the **end** of the report. First report what was completed, evidence and any blocker; then show one `ACTION REQUIRED` section only if a real owner decision remains.

When the owner must run or enter something, provide the exact copyable command/authorization in a fenced `bash` block. Do not bury the requested action inside explanatory prose.

## Merge invariant

Merge remains an explicit owner decision and never authorizes deployment, database writes/migrations, host/root mutation, service activation, secrets/credentials, Cloudflare mutation, firmware activation, physical actuation, external-account mutation, or another live write.
