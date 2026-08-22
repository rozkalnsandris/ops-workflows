# FAST-LANE v2.2 Composite — decision record, migration rationale, and operating history

**Status:** Accepted  
**Decision date:** 2026-08-22  
**Canonical repository:** `rozkalnsandris/ops-workflows`  
**Active policy:** `docs/FAST_LANE_V2_1_HYBRID.md` (compatibility filename; contents are v2.2)  
**Machine contract:** `policy/fast-lane-v2.2.json`

## 1. Purpose of this record

This document explains **why FAST-LANE v2.2 was necessary**, what failed or became inefficient under v2.1, what exact behavior v2.2 changes, and what must remain invariant in future implementations.

It is intentionally more detailed than the normative policy. The normative policy says **what to do**. This record preserves **why the rules exist**, including the concrete 2026-08-22 Control Center and cross-repository rollout evidence that caused the change.

The central design rule is:

> **The human approves the RISK / DECISION. Automation executes the TECHNICAL STEPS.**

Equivalent negative rule:

> **Do not make the human approve every technical checkpoint.**

FAST-LANE exists to reduce unnecessary operator interaction without weakening merge, production, host, credential, permission, database, device, or other trust-boundary controls.

---

## 2. What FAST-LANE v2.1 solved

FAST-LANE v2.1 Hybrid was a useful and necessary first phase. It established a shared distinction between:

- **FAST** — source-only work that may continue through Ready when it does not expand authority or perform live mutation;
- **STRICT** — work involving production/runtime authority, host/root, database writes or migrations, secrets, Cloudflare mutation, firmware/device activation, physical actuation, external-account mutation, or equivalent trust-boundary changes.

v2.1 also introduced or reinforced these useful controls:

- source work may proceed as one coherent flow to Ready;
- 2–5 tightly related same-risk source work items may be combined into one reviewable PR;
- up to two scope-preserving corrective commits may be made after CI/review findings without returning to the owner;
- merge remains a separate explicit owner decision;
- merge never implies deploy or another live mutation;
- mutable GitHub state is refreshed before merge;
- one Ready receipt is preferred over repeated status narration.

This materially improved the **source side** of the workflow.

A representative Control Center example was PR `rozkalns-control-center#375`: source work reached Ready with exact-head CI PASS, no unresolved review threads, and one clear merge gate. This is the part of v2.1 that worked and is retained in v2.2.

---

## 3. The design gap in v2.1

The problem was not that v2.1 classified risk incorrectly. The problem was that it did not define the relationship between **STRICT risk** and **human interaction count** precisely enough.

The original Control Center v2.1 adoption, PR `rozkalns-control-center#367`, explicitly said:

- FAST/STRICT would be adopted;
- production/GitHub/Cloudflare/RPi5 approval invariants would remain;
- and, critically, **current CI and production preflight/reconcile workflows would remain unchanged in Phase 1**.

That meant v2.1 optimized source delivery but intentionally left the post-merge live workflow structurally unchanged.

The missing rule was:

> **STRICT describes the mutation risk, not the number of human gates.**

Without that sentence, a conservative implementation could mechanically transform every technical checkpoint into a separate owner interaction.

The resulting anti-pattern looked like this:

```text
merge
→ run separate preflight script
→ owner returns output
→ inspect checkout
→ ask owner for fast-forward authorization
→ owner returns output
→ ask owner for deploy authorization
→ run rollout
→ owner returns output
→ reconcile
```

Every individual step could be justified as “safe” or “STRICT-aware”, but the combined workflow was operationally poor. The owner became a transport layer between deterministic technical steps.

That contradicted the purpose of FAST-LANE.

---

## 4. Concrete evidence from Control Center

### 4.1 PR #374 — deploy intent existed, but local checkout state was discovered too late

`rozkalns-control-center#374` was a source change whose PR explicitly classified:

- production deploy: **YES after merge**;
- merge does **not** authorize deploy.

That separation was correct.

The operational problem appeared after the merge/deploy decision chain: the trusted Lenovo checkout was later found to be stale. Because checkout discovery and synchronization had been treated as a separate operational phase, this produced an additional diagnostic step and an additional authorization interaction.

The lesson was not “allow arbitrary Git commands”.

The lesson was:

> discover all possible read-only state before asking for live authority, and allow one precise live authorization to include the tightly coupled mutation categories that are actually required.

For a trusted checkout, that can mean an envelope that explicitly permits only:

```text
git fetch
git merge --ff-only origin/main
```

followed by the bounded production rollout, while still forbidding:

```text
git reset
git rebase
git clean
force update
history rewrite
unlisted host changes
secret changes
permission changes
```

`git fetch` changes local Git metadata and therefore counts as a mutation for authorization-consumption purposes. It is not a reason to create a separate human decision gate.

### 4.2 PR #375 — the source FAST flow was good; the post-merge workflow was not

`rozkalns-control-center#375` demonstrated the desired source behavior:

```text
turpini
→ source change
→ tests
→ Draft PR
→ exact-head CI PASS
→ Ready receipt
→ one MERGE decision
```

The PR recorded:

- exact head `325ad5f51ddf1f65d26f8532ed229b82b837e7cd`;
- CI run `32585716366` PASS;
- 0 unresolved review threads;
- deploy required: YES;
- permission/trust-boundary change: NO;
- merge explicitly did not authorize production rollout.

The inefficiency came **after** the source work. A literal STRICT interpretation risked creating a new owner gate for preflight, another for checkout synchronization, and another for deployment.

That is the specific behavior v2.2 was created to prevent.

### 4.3 The obsolete separate-preflight pattern

During the discussion, a prepared script named like:

```text
control_predeploy_readonly_375_v1.sh
```

was identified as belonging to the fragmented model.

The v2.2 decision is that this kind of read-only preflight logic should normally be **inside the beginning of the one-shot rollout controller**, before the first mutation, rather than being a separate user-driven session.

The script name is recorded here as historical evidence only. It is not a canonical tool and must not be assumed to exist or be appropriate in future sessions.

---

## 5. The v2.2 design objective

FAST-LANE v2.2 Composite keeps the same trust boundaries but optimizes the human interface.

The desired normal flow is:

```text
START / turpini
      │
      ▼
FAST SOURCE ENVELOPE
fresh GitHub state
→ branch
→ implementation
→ tests
→ Draft PR
→ CI/review
→ up to 2 bounded corrections
→ Ready
      │
      ▼
STOP #1 — MERGE AUTHORIZATION
      │
      ▼
exact-head merge
      │
      ▼
POST-MERGE READ-ONLY EVIDENCE
      │
      ├── Deploy/live mutation = NO → DONE
      │
      └── Deploy/live mutation = YES
              │
              ▼
STOP #2 — COMPOSITE LIVE AUTHORIZATION
              │
              ▼
ONE-SHOT FAIL-CLOSED EXECUTION
preflight
→ exact target/SHA/baseline checks
→ allowed checkout sync if needed
→ deterministic build
→ one exact candidate/version
→ automated candidate verification
→ drift guard
→ one bounded rollout
→ read-only reconciliation
→ final receipt
              │
        PASS → DONE
        ERROR/DRIFT/NEW RISK → STOP
```

This is the meaning of “Composite” in v2.2: tightly coupled technical mutations for one owner-approved live decision may be executed inside one bounded envelope.

It does **not** mean that unrelated risky actions are bundled together.

---

## 6. Human gate budget

The normal end-to-end path has a budget of at most two owner gates:

1. **MERGE**
2. **COMPOSITE LIVE**, only if live mutation is required.

This is a guardrail against process regression.

### 6.1 What is not a human gate

The following are technical checkpoints and should be automated whenever the tooling allows it:

- CI polling;
- GitHub mutable-evidence refresh;
- GET/read-only preflight;
- diff inspection;
- checkout discovery;
- clean working-tree checks;
- ancestor checks;
- read-only production baseline reads;
- build preparation;
- candidate GET verification;
- version/deployment reads;
- reconciliation;
- receipt construction.

A read-only checkpoint may fail and block progress, but its existence alone does not justify asking the owner to approve it.

### 6.2 When a STOP is legitimate

A STOP is justified when:

- exact merge authorization is required;
- exact Composite Live authorization is required;
- an authorized mutation has started and an error or ambiguous result occurs;
- a new target, SHA, scope, mutation category, trust boundary, or risk class appears.

A technical step does not become a “decision” merely because it is important.

---

## 7. Composite Live authorization envelope

A live authorization must be precise enough that execution can continue without improvising.

At minimum, bind:

- repository;
- exact approved Git SHA/ref;
- exact target/environment/device/account;
- expected authoritative pre-mutation baseline, when available;
- allowed mutation categories;
- hard operation/mutation count limits where practical;
- explicit exclusions.

Example:

```text
repo: rozkalnsandris/rozkalns-control-center
approved_sha: <exact 40-char SHA>
target: <exact Worker/environment>

allowed local mutation:
- git fetch
- git merge --ff-only origin/main

allowed production mutation:
- maximum 1 version upload
- maximum 1 deployment of the exact verified uploaded version

forbidden:
- reset
- rebase
- clean
- force/history rewrite
- secret changes
- permission changes
- D1 mutation
- Queue mutation
- DNS/Tunnel/Access changes
- unrelated host changes
```

The envelope is the owner’s decision boundary.

Automation may select deterministic implementation details **inside** that boundary. It may not expand the boundary.

---

## 8. Exact SHA, target, and baseline are anti-TOCTOU controls

A vague authorization such as “deploy main” is insufficient for a high-value production mutation if `main` can move between approval and execution.

v2.2 requires exact binding wherever practical:

```text
approved SHA
+
approved target
+
expected baseline
```

Immediately before live mutation, those conditions are re-read.

If they changed:

```text
FAIL CLOSED
→ preserve evidence
→ STOP
```

Do not silently reinterpret approval to mean a newer `main`, a different target, or a different production baseline.

This is a time-of-check/time-of-use control, not bureaucratic ceremony.

---

## 9. One-shot execution model

The preferred live controller is one script/job/controller invocation that performs the technical sequence after the owner makes the live decision.

A typical sequence is:

1. verify exact GitHub/main/CI evidence;
2. read production/runtime baseline;
3. verify local checkout state;
4. perform only pre-authorized `fetch` + `merge --ff-only` if required;
5. revalidate approved SHA/target/baseline;
6. build with the project-controlled toolchain;
7. create/upload exactly one candidate artifact/version;
8. capture the exact artifact/version ID;
9. verify that exact candidate automatically;
10. re-read production baseline / concurrency guard;
11. perform exactly one bounded rollout of the verified artifact/version;
12. GET/read-only reconciliation;
13. emit one final receipt.

All fail-closed checks that can be performed before the first mutation should be performed before it.

The owner should not need to copy intermediate output from one technical stage into the next chat turn.

---

## 10. Build once, verify once, deploy the exact verified artifact

Cloudflare Workers exposes a useful separation:

```text
version ≠ deployment
```

A version can be uploaded/created without immediately making it the production deployment. This supports:

```text
exact Git SHA
→ deterministic build
→ one version upload
→ capture VERSION_ID
→ preview/candidate verification of VERSION_ID
→ deploy that same VERSION_ID
```

Do not verify one build and deploy a different rebuild when the platform supports immutable or identifiable artifacts/versions.

The same principle applies beyond Cloudflare: the thing that passed candidate verification should be the thing promoted.

---

## 11. Candidate verification is a technical checkpoint, not a new owner gate

Where the platform supports a preview/version-specific endpoint, candidate validation should run inside the Composite Live envelope.

Example outcome:

```text
version upload succeeded
candidate verification failed
production unchanged
→ preserve candidate/version evidence
→ STOP
```

The owner is needed because execution failed, not because candidate verification itself requires approval.

---

## 12. Concurrency and drift guard

A live target should not have multiple uncontrolled rollout owners.

Immediately before the production write, re-read the authoritative current baseline if the platform exposes it.

If another actor changed production since the approved baseline was collected:

```text
STOP
```

Do not adapt the rollout automatically to a new, unapproved baseline.

For GitHub Actions implementations, a production deployment should also use an appropriate `concurrency` group or equivalent control so only the intended rollout owns the target at a time.

---

## 13. Mutation start and authorization consumption

The one-time Composite Live authorization is considered consumed when the **first state-changing command** starts successfully.

Examples of mutation include:

- `git fetch` in the trusted checkout;
- a fast-forward merge;
- artifact/version upload;
- production deployment;
- host/service change;
- database write;
- external-account write.

Read-only actions do not consume the live mutation authorization.

Examples of read-only actions:

- GitHub GET/search/status reads;
- CI polling;
- version/deployment list;
- HTTP GET preflight;
- diff inspection;
- local `git status`;
- ancestor checks;
- production baseline GET.

This distinction mattered during the 2026-08-22 rollout, described below.

---

## 14. Failure semantics after mutation start

After the first authorized mutation begins, any of these require STOP:

- command error;
- ambiguous result;
- unexpected target drift;
- unexpected SHA drift;
- new required mutation category;
- new trust-boundary condition;
- inability to prove whether production/runtime changed.

Default response:

```text
preserve evidence
→ STOP
```

Default response is **not**:

```text
retry
→ rollback
→ cleanup
→ alternate deploy path
→ reset/rebase
```

Those are additional mutations and require explicit pre-authorization unless a project-specific, proven-safe contract says otherwise.

---

## 15. Rollback is not implicitly authorized

Rollback is itself a production mutation.

For Cloudflare Workers, rollback creates a new deployment of the selected prior version. In addition, Worker versions do not include the mutable state of external storage resources such as D1/KV/R2/Durable Objects.

Therefore a code rollback can be semantically unsafe if associated state changed.

Default v2.2 behavior:

```text
live error
→ preserve evidence
→ STOP
```

A future project may define a `ROLLBACK_SAFE` class, but only with explicit prerequisites and explicit owner authorization.

---

## 16. Toolchain determinism

Deployment tooling should be project-local and version-controlled/pinned where practical.

For Cloudflare Workers, Wrangler should be installed locally in the project. Running `npx wrangler` when Wrangler is not installed locally may select the latest available Wrangler version, changing deploy semantics at the worst possible time.

The broader invariant is:

> live execution should not introduce a new unreviewed tool version while performing the authorized rollout.

For GitHub Actions, third-party actions/reusable workflows should be pinned to full immutable commit SHAs where applicable.

---

## 17. Receipt contract

The owner should receive one concise final receipt, not a stream of technical checkpoint output.

Example successful live receipt:

```text
RESULT=PASS

REPO=<repo>
APPROVED_GIT_SHA=<sha>
OBSERVED_GIT_SHA=<sha>
TARGET=<target>

LOCAL_BEFORE_SHA=<sha>
LOCAL_AFTER_SHA=<sha>
LOCAL_SYNC=NONE|FF_ONLY

PROD_BEFORE_VERSION=<id>
CANDIDATE_VERSION=<id>
PROD_AFTER_VERSION=<id>

VERSION_UPLOAD_COUNT=1
DEPLOYMENT_COUNT=1

CANDIDATE_VERIFY=PASS
POST_DEPLOY_RECONCILIATION=PASS

FIRST_MUTATION_STARTED=YES
AUTHORIZATION_CONSUMED=YES
UNAUTHORIZED_MUTATIONS=0
```

Example failure fields:

```text
RESULT=FAIL
FAILED_STAGE=<stage>
FIRST_MUTATION_STARTED=YES|NO
AUTHORIZATION_CONSUMED=YES|NO
PRODUCTION_CHANGED=YES|NO|UNKNOWN
NEXT_ACTION=STOP_OWNER_REVIEW
```

The exact fields may vary by project, but the receipt must make the state and next human decision unambiguous.

---

## 18. Operator UX rule

When a human decision is required:

1. first report what was completed;
2. report the relevant evidence/blocker;
3. put the decision **at the end**;
4. make it visually obvious;
5. provide the exact input in a fenced `bash` block when practical.

Preferred shape:

````text
[status/evidence]

## ACTION REQUIRED

```bash
MERGE repo#123@<exact-sha>
```
````

Do not bury the requested action in the middle of a long explanation.

This UX requirement is part of the policy, not cosmetic formatting. It prevents the operator from missing the actual decision and reduces accidental ambiguous authorization.

---

## 19. State machine

The shared conceptual state machine is:

```text
SOURCE_FAST
   ↓
READY_MERGE
   ↓
WAITING_MERGE_AUTH
   ↓
POST_MERGE_READONLY
   ↓
WAITING_COMPOSITE_LIVE_AUTH   (only if live mutation is required)
   ↓
LIVE_EXECUTING
   ↓
DONE
```

Failure path:

```text
LIVE_EXECUTING
   ↓
STOP_ERROR
```

Important transitions:

- `SOURCE_FAST → READY_MERGE` may be automated under normal FAST continuation.
- `READY_MERGE → merge` requires explicit owner merge authority.
- `POST_MERGE_READONLY → DONE` needs no additional owner gate if no live mutation is required.
- `POST_MERGE_READONLY → LIVE_EXECUTING` requires one Composite Live authorization.
- `LIVE_EXECUTING → STOP_ERROR` never silently loops back into mutation.

---

## 20. Anti-patterns explicitly rejected by v2.2

### Anti-pattern A — gate every command

```text
approve preflight
approve checkout check
approve fetch
approve build
approve upload
approve candidate check
approve deployment
approve reconciliation
```

Rejected because technical checkpoints are being confused with human decisions.

### Anti-pattern B — vague “deploy latest main”

Rejected because the approved object can change between decision and mutation.

### Anti-pattern C — separate read-only preflight session as the normal path

Rejected because it turns the owner into a command/output courier.

### Anti-pattern D — rebuild after candidate verification

Rejected when an exact verified artifact/version can be promoted.

### Anti-pattern E — automatic rollback after an unexpected live failure

Rejected unless rollback was explicitly pre-authorized and proven safe.

### Anti-pattern F — continue after drift because “the change is probably harmless”

Rejected. Drift is a new state and therefore a new decision boundary.

### Anti-pattern G — ask the owner to re-approve because a read-only poll or GET occurred

Rejected. Read-only technical work is not a new risk decision.

---

## 21. 2026-08-22 rollout history — evidence that v2.2 works

This section records the migration session that established v2.2 across the owner repositories.

### 21.1 Scope discovery corrected the assumed repository count

The initial historical search found 12 repositories with v2.1 adoption activity.

Fresh canonical-main inspection then showed that two of those repositories — `rozkalnsandris` and `YouTube_Marcim` — did not actually have v2.1 merged into `main`.

Their old adoption PRs had been closed, and no new duplicate PRs were created merely to satisfy an assumed count.

Therefore the actual rollout set was **10 repositories where FAST-LANE had really been adopted**.

This is an important canonical-state lesson:

> intended rollout history does not override current repository truth.

### 21.2 Canonical v2.2 source PR

`rozkalnsandris/ops-workflows#6` introduced the canonical shared v2.2 policy and machine-readable contract.

During its source validation, CI initially failed because the repository’s own policy self-test still expected v2.1 markers.

That failure was:

- source-only;
- scope-preserving;
- inside the existing correction budget.

The test was updated to validate the v2.2 contract, and the new exact-head CI passed.

No owner gate was introduced for this technical source correction.

This is a direct example of the FAST correction rule working as intended.

### 21.3 Read-only tooling error did not consume merge authority

During the first batch merge attempt, an incorrect read-only GitHub reactions endpoint returned `403 Resource not accessible by integration`.

No GitHub write or merge had started at that point.

Therefore:

```text
FIRST_MUTATION_STARTED=NO
AUTHORIZATION_CONSUMED=NO
```

The incorrect read-only path was abandoned and the proper PR/check/review evidence endpoints were used.

The important rule is not “ignore read errors”. The rule is:

> a read-only tooling failure before mutation does not consume the mutation authorization; resolve or replace the read path without inventing a new owner approval unless the blocker itself requires a decision.

### 21.4 First batch merge: exact-head drift triggered the designed STOP

The first batch authorization included `dashboard_RPi5#193` at an older exact head:

```text
a6ec30f7f0ff9ef55aaccbe223d4ee96fff7d2ff
```

The first authorized mutation in that batch was the successful squash merge of `ops-workflows#6`.

After that mutation, fresh pre-merge inspection of `dashboard_RPi5#193` showed the PR head had moved to:

```text
57964d721f1794113c4d9ccef0c09762b8da1cd9
```

Because the authorized exact head no longer matched, the batch stopped.

No attempt was made to reinterpret the old authorization as permission to merge the new head.

That STOP was intentional proof of the v2.2 invariant:

```text
mutation started
+
later target SHA differs from authorized SHA
→ preserve evidence
→ STOP
→ require new exact authorization
```

### 21.5 Read-only recalculation discovered another stale assumption

After the STOP, the owner gave a generic `turpini`, which authorized only safe/read-only continuation.

Fresh recalculation found that `rozkalns-control-center#376` had already been merged independently before the `ops-workflows#6` batch mutation began.

Therefore it was removed from the remaining merge set instead of being re-authorized or touched again.

The actual remaining set became 8 PRs, not 9.

Again, fresh GitHub state overrode stale chat assumptions.

### 21.6 Second exact-head batch completed successfully

The owner then authorized one exact remaining batch.

Each PR was revalidated immediately before its squash merge:

- open / Ready;
- exact head matches authorization;
- mergeable;
- CI PASS where the repository has PR CI;
- reviews / unresolved review threads clear.

The remaining 8 merges completed without drift or error.

No production, Cloudflare, host, database, secret, permission, external-account, firmware, or device mutation was performed as part of this policy rollout.

---

## 22. Final v2.2 rollout inventory from the 2026-08-22 session

The canonical v2.2 policy or repository-local v2.2 adoption was merged in these 10 actual adopter repositories:

| Repository | PR | Merge commit |
| --- | ---: | --- |
| `ops-workflows` | #6 | `646eaacfd478232b0c87e500841ced64f459b850` |
| `rozkalns-control-center` | #376 | `9d4fb5ac56a946bcf278ff1ffa0781247dc1a97b` |
| `dashboard_RPi5` | #193 | `2d6e4f4505bfb524843c88d48973054d7cd5ac49` |
| `hermes-deals` | #751 | `07a0494dbe82c15b91feb84377ab6aca43f9586a` |
| `hermes-tech` | #142 | `7bc056e3dcb17143653038e31ebe665983e61127` |
| `home-assistant-config` | #133 | `6244ce7dee15cb697e928b8517b871e3f7981a3b` |
| `balcony-irrigation-esp32` | #38 | `7690c01d1146f72e7771b75ba0d5e1b7d4d93cbc` |
| `RPi5_main` | #208 | `9e4390b50c7dae2eeaea5f0eeca4bb35a0e9b8c7` |
| `rozkalns-cv` | #386 | `7c37468a67f25ce77993a415a80abc44293a7aee` |
| `hermes-email-skill` | #2 | `81506456e55528f92f13713a6319b5f170344421` |

This table is a historical receipt, not a substitute for fresh GitHub state. Future work must still re-read each repository.

---

## 23. Why Control Center has stronger/local detail

The cross-project policy defines the shared human-gate and execution semantics.

`rozkalns-control-center` also records repository-local detail because its live path can involve:

- trusted Lenovo checkout synchronization;
- Cloudflare Worker version upload;
- candidate GET verification;
- exact-version deployment;
- GET-only reconciliation.

That repository may therefore describe a concrete Composite Live envelope and one-shot sequence more specifically than this shared baseline.

Repository-local rules may be stricter.

They may not weaken the shared invariant that merge and live authority are separate.

---

## 24. External platform alignment

v2.2 was checked against current official platform documentation on 2026-08-22.

### GitHub Actions deployment model

GitHub environments and deployment protection rules support an approval gate before a deployment job proceeds. The approval is a job/environment decision boundary; the protected job then performs its technical steps.

References:

- https://docs.github.com/en/actions/reference/workflows-and-actions/deployments-and-environments
- https://docs.github.com/en/actions/how-tos/deploy/configure-and-manage-deployments/control-deployments
- https://docs.github.com/en/actions/how-tos/deploy/configure-and-manage-deployments/review-deployments

This aligns with the v2.2 idea of **one human live decision followed by automated technical execution**.

### GitHub concurrency

GitHub supports concurrency controls that can ensure only one deployment/job in a concurrency group runs at a time.

References:

- https://docs.github.com/en/actions/concepts/workflows-and-actions/concurrency
- https://docs.github.com/en/actions/how-tos/deploy/configure-and-manage-deployments/control-deployments

This supports the v2.2 drift/concurrency guard.

### Cloudflare Worker versions and deployments

Cloudflare explicitly separates a Worker **version** from a **deployment**. A version can be created/uploaded and verified before it is promoted to production traffic.

References:

- https://developers.cloudflare.com/workers/versions-and-deployments/
- https://developers.cloudflare.com/workers/versions-and-deployments/preview-urls/

This supports:

```text
build once
→ upload/create exact version
→ verify exact version
→ deploy exact same version
```

### Cloudflare rollback semantics

Cloudflare rollback creates a new deployment of the selected prior version.

Reference:

- https://developers.cloudflare.com/workers/versions-and-deployments/rollbacks/

This supports treating rollback as a new live mutation rather than an implied automatic error handler.

### Wrangler installation

Cloudflare recommends installing Wrangler locally in each project, which keeps the project and team on the same controlled Wrangler version. Cloudflare also warns that `npx wrangler` can use the latest version if Wrangler is not installed.

Reference:

- https://developers.cloudflare.com/workers/wrangler/install-and-update/

This supports the v2.2 toolchain-determinism requirement.

### GitHub action pinning

GitHub recommends pinning third-party Actions to full commit SHAs for immutable execution.

Reference:

- https://docs.github.com/en/actions/reference/security/secure-use

This is consistent with the broader exact-version/exact-SHA philosophy used by v2.2.

---

## 25. What v2.2 does not authorize

FAST-LANE v2.2 is a process model. It is not blanket authority.

It does not by itself authorize:

- merge;
- production deployment;
- host/root mutation;
- service/systemd/Docker/network mutation;
- database writes/migrations;
- secret or credential changes;
- permission/identity/trust-boundary expansion;
- Cloudflare DNS/Tunnel/Access mutation;
- firmware activation;
- physical actuation;
- external-account writes;
- destructive cleanup;
- history rewrite.

Those actions remain controlled by repository-local rules and explicit owner authority.

---

## 26. How to interpret `turpini`

For repositories using this policy, a generic continuation command such as:

```text
turpini
```

means:

> continue safe/read-only/source-level work through the next genuine human decision boundary.

It does not mean:

> merge, deploy, mutate production, alter secrets, change permissions, or cross a trust boundary.

This allows the automation to do useful work without repeatedly asking permission for deterministic source/read-only steps.

---

## 27. Decision display convention

The operator-facing response should avoid mixing status and authorization text.

Preferred:

````text
Done:
- source updated
- CI PASS
- reviews clear
- exact head verified

Not done:
- merge
- deploy

## ACTION REQUIRED

```bash
MERGE repo#123@<exact-head-sha>
```
````

After merge, if live mutation is required:

````text
Read-only preflight complete.
Exact SHA/target/baseline verified.

## ACTION REQUIRED

```bash
AUTHORIZE COMPOSITE LIVE ...
```
````

This format is deliberately easy to copy and difficult to misread.

---

## 28. Future change rule

Do not silently reinterpret or weaken v2.2.

If a future change alters any of these invariants, treat it as a new policy version or explicit policy change:

- normal owner gate budget;
- distinction between read-only checkpoints and owner decisions;
- exact-SHA/target binding;
- mutation-start authorization consumption;
- post-mutation STOP semantics;
- no automatic retry/rollback default;
- build-once/exact-artifact promotion;
- drift/concurrency guard;
- merge/live separation;
- end-of-report decision UX.

A future v2.3 may improve automation, but it should explain exactly which v2.2 problem it solves and preserve historical rationale rather than rewriting this record.

---

## 29. Short canonical summary

If only five rules are remembered, remember these:

1. **Human approves risk/decision; automation executes technical steps.**
2. **Normal human gates are MERGE and, only when necessary, one COMPOSITE LIVE gate.**
3. **Bind live authority to exact SHA, exact target, bounded mutations, explicit exclusions, and baseline when available.**
4. **After first mutation, unexpected error/drift/new risk means preserve evidence and STOP — no implicit retry/rollback.**
5. **Put the next human decision at the end, clearly visible and copyable.**

That is why FAST-LANE v2.2 exists.
