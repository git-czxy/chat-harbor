# ChatHarbor 0.0.11.0 — Automated Regression Report

Status: **PASS — automated regression**

Real-browser smoke is still required for the provider's current live endpoint behavior, IndexedDB persistence, and the first 0.0.10.x → 0.0.11.0 convergence run.

## New convergence / efficiency checks

- PASS list-observation checkpoint can commit via `OBSERVATION_ONLY` without rewriting conversation files
- PASS next identical preflight converges to `UNCHANGED` with zero required detail fetches
- PASS list/detail timestamp facts are separated instead of feeding one source back into another source's comparator
- PASS Manifest-only observation commit preserves previous content `synced_at`
- PASS remote archive-state conflict preserves `unknown`
- PASS conflicting known project memberships preserve `unknown` instead of arbitrarily choosing one
- PASS attachment completeness is independent from content state
- PASS attachment-unknown record stays `UNCHANGED` when attachment download is disabled
- PASS enabling attachment download turns an incomplete/unknown attachment record into a verification/backfill candidate
- PASS Manifest-first local scan fast-checks tracked JSON without reparsing it
- PASS untracked JSON remains discoverable and duplicate identity remains blocking
- PASS remote-head fingerprint is order-independent and detects metadata/update changes
- PASS persistent Remote Index cache markers, 20-item head window, periodic full refresh, sync freshness and force-full path exist
- PASS first-stage status filter is no longer forced to `待处理`, so `已同步` can remain visible after preflight

## Preserved regression checks

- PASS Layout v1 → v2 local-only migration
- PASS v2 `conversations/` + `projects/<project>/` namespace paths
- PASS byte-identical JSON / Markdown / tracked assets after migration
- PASS untracked legacy preservation and resumable migration
- PASS Planner classification matrix and LOCAL_ONLY safety
- PASS candidate-only detail fetch
- PASS streaming Fetch → Classify → Atomic Commit → Manifest
- PASS write → Manifest commit → tracked-only cleanup ordering
- PASS Manifest-failure cleanup barrier
- PASS conservative defaults 6–10s / batch 20 / 180–300s
- PASS retry, pause/resume, safe cancel
- PASS absolute wall-clock deadlines, wake guard and MM:SS batch countdown
- PASS run-state locking for network/attachment/filter/selection controls
- PASS injected JavaScript syntax

## Expected first real run

Older 0.0.10.x Manifest records do not have the new `remote_list_*` checkpoint fields or authoritative `attachment_state`.

Therefore:

1. records whose legacy detail time differs from current list time may need one transition verification;
2. an unchanged verified record should receive an `OBSERVATION_ONLY` Manifest commit and should not repeat verification next run;
3. attachment state remains `unknown` for legacy records unless inspected; with default no-download this does not add verification;
4. enabling attachment download can intentionally cause a one-time attachment verification/backfill pass.

## Build-environment note

The package contains a fail-closed build script. It downloads only the fixed huhusmang upstream commit and the patcher verifies Git blob `3a5dfe6a696e03db7028232d45b136104e67b51f` before producing the userscript.

This execution environment cannot resolve the raw GitHub host, so the final merged `.user.js` was not fabricated locally. The patcher, extracted injected JavaScript layer, and all automated regressions were validated here; run `prepare_clean_integrated_sync.ps1` on the normal Windows machine to generate the installable userscript.

Injected layer SHA-256:

```text
4d9af208b6435a71c49a389166552aab86d85ca3f87a011081408ffef5f38740
```
