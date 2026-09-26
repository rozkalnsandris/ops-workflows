# GitHub API Access v1 — rollout acceptance matrix

Status: SOURCE CLOSEOUT CANDIDATE  
Tracking: `ops-workflows#108`, rollout slice `ops-workflows#112`  
Accepted shared contract revision: `3bb0740b5f0a8ce631d2ff79f1acc4999ff6ed2c`

## Scope

This matrix records the controlled source/governance rollout of the accepted GitHub API Access v1 contract across the active Agent Work Cycle repository set from `ops-workflows#112`.

It is evidence of source adoption only. It does not grant or imply LIVE/deploy/runtime, secrets, permissions, repository-settings, database, network, Cloudflare, device, firmware, or host mutation authority. Repository-local stricter rules remain authoritative.

The exact accepted consumer `main` SHA below is the post-merge identity observed during that repository's rollout lane. These values are acceptance receipts, not a promise that the repository will remain at that SHA later. Normal future work must freshly read current GitHub state.

## Acceptance matrix

| Repository | Adoption mechanism | Shared revision | Local stricter rule reference | Source PR | Exact accepted main SHA | CI | Rollout state | Blocker / next step |
|---|---|---|---|---:|---|---|---|---|
| `ops-workflows` | Canonical human + machine contract (`docs/GITHUB_API_ACCESS_V1.md`, policy/tests) | `3bb0740b5f0a8ce631d2ff79f1acc4999ff6ed2c` | `AGENTS.md` shared FAST/STRICT, merge/LIVE and mutation-ambiguity rules | `#113`, `#114`, `#116` | `3bb0740b5f0a8ce631d2ff79f1acc4999ff6ed2c` | SUCCESS | ACCEPTED | Canonical producer; this closeout PR records fleet evidence only. |
| `RPi5_main` | Repository-local API-access manifest + policy/test adoption | `3bb0740b5f0a8ce631d2ff79f1acc4999ff6ed2c` | Local explicit merge/LIVE/runtime trust boundary in `AGENTS.md` | `#735` | `634db86a60ec2942b3f4d9f552c639f9412338a4` | SUCCESS | ACCEPTED | None. |
| `hermes-deals` | Repository-local API-access manifest + startup/test integration | `3bb0740b5f0a8ce631d2ff79f1acc4999ff6ed2c` | Local merge and LIVE/deploy authority rules | `#939` | `5307243b6829496b3cc879d75176540b7d1eedd3` | SUCCESS | ACCEPTED | None. |
| `hermes-tech` | Repository-local API-access manifest + startup/test integration | `3bb0740b5f0a8ce631d2ff79f1acc4999ff6ed2c` | Local merge and LIVE/deploy authority rules | `#163` | `5abd8774981017eb7c91bcd3d01dd2aad685027b` | SUCCESS | ACCEPTED | None. |
| `rozkalns-cv` | Repository-local API-access manifest + startup/test integration | `3bb0740b5f0a8ce631d2ff79f1acc4999ff6ed2c` | Local merge and production publication/deploy rules | `#488` | `0eff7f298b4e52b021c7f98a4d8ecf6df2405e34` | SUCCESS | ACCEPTED | None. |
| `rozkalns-control-center` | Repository-local API-access manifest + TypeScript policy validation | `3bb0740b5f0a8ce631d2ff79f1acc4999ff6ed2c` | Local explicit merge/LIVE/trust-boundary rules | `#777` | `f5a36b3c0790d666e5402dc74bb7b472224e613a` | SUCCESS | ACCEPTED | None. |
| `dashboard_RPi5` | Repository-local API-access manifest + `start-github-only` routing + tests | `3bb0740b5f0a8ce631d2ff79f1acc4999ff6ed2c` | Local explicit merge and separate production trust boundary | `#291` | `b970c1cff83655320c0f3c9bfcee1860e300c89c` | SUCCESS | ACCEPTED | None. |
| `RPi5-maintenance` | Repository-local API-access manifest + Python contract test + Makefile gate | `3bb0740b5f0a8ce631d2ff79f1acc4999ff6ed2c` | `AGENTS.md` explicit MERGE and separate RPi5 LIVE mutation gate | `#66` | `ed5a5cc5592c30ed82ced26e6a87d7809e8dc10a` | SUCCESS | ACCEPTED | Existing production observation lane remains separate and unchanged. |
| `home-assistant-config` | Repository-local API-access manifest + startup routing + Python contract test | `3bb0740b5f0a8ce631d2ff79f1acc4999ff6ed2c` | Local explicit merge; HA `/config`, restart/recreate, `.storage`, secrets and runtime changes remain separate LIVE authority | `#153` | `6f7797aae521b9d24b241bf5f26bc64457cb4ba6` | SUCCESS | ACCEPTED | Production deploy/change classification for this source-only rollout: NO. |
| `balcony-irrigation-esp32` | Repository-local API-access manifest + startup routing + synthetic ambiguity test in firmware CI | `3bb0740b5f0a8ce631d2ff79f1acc4999ff6ed2c` | Local explicit merge and separate flash/OTA, MQTT/Home Assistant and physical relay/pump LIVE gates | `#59` | `1d33e702fbb656fa39a55ad8795156cdcddcacd0` | SUCCESS | ACCEPTED | No device/firmware LIVE action was part of rollout. |
| `rozkalns_weather` | Canary API-access manifest + managed Agent Work Cycle adoption + governance tests | `3bb0740b5f0a8ce631d2ff79f1acc4999ff6ed2c` | Weather FAST/AUTO-RUN FULL rules; merge and LIVE remain repository-local and separately gated | `#206` | `0a917ace59fc4d9b31703c4e12288e5fd0176de3` | SUCCESS | ACCEPTED | Canary passed; no LIVE/deploy authority created. |
| `linux-operations-lab` | API-access manifest + startup routing + synthetic 429/timeout/transport test + focused Actions gate | `3bb0740b5f0a8ce631d2ff79f1acc4999ff6ed2c` | Local explicit MERGE and separate LIVE/runtime authority; no real household/production-like disruption | `#2` | `639bd6dd5f6ee325e292526bf43371d84d58ccc2` | SUCCESS | ACCEPTED | None. |

## Acceptance summary

All repositories in the active `ops-workflows#112` rollout set are recorded as `ACCEPTED`; there are no remaining `PENDING`, `READY`, or `BLOCKED` consumers in this slice.

The rollout preserved these invariants across consumers:

- START/SYNC retrieval is minimum-sufficient and serial by default;
- changed-file enumeration is on demand rather than part of every refresh;
- CI/review continuation avoids tight polling;
- stable rate-limit/read dispositions are available through the shared contract;
- final pre-mutation refresh is compact and exact-head bound;
- mutation ambiguity is fail-closed and does not authorize duplicate writes;
- synthetic ambiguous `429`/timeout/transport scenarios cover the no-duplicate-mutation path where practical;
- merge authority remains repository-local;
- merge does not imply LIVE/deploy authority;
- no consumer received widened secrets, permissions, repository-settings, runtime or production authority from this rollout.

## Slice D closeout

With the Weather canary accepted and every intended active repository recorded above as accepted, `ops-workflows#112` meets its source/governance rollout Definition of Done, subject to normal review/CI/merge of this closeout record.

After this closeout record is accepted on `main`, the umbrella `ops-workflows#108` can be reconciled against Slices A–D and closed if its Definition of Done remains satisfied by fresh GitHub evidence.
