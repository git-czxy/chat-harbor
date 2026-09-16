# ChatHarbor 0.0.9.3 Test Report

Date: 2026-09-14

Scope: UI-clarity hotfix over 0.0.9.2. No intentional change to Planner, content classification, Directory Writer, Manifest transaction order, LOCAL_ONLY protection, conservative pacing, streaming commit, pause/resume/cancel, wake handling, or batch countdown.

## New regression checks

- PASS — runtime phase wording uses `当前第 X / N 条 · 阶段`, avoiding ambiguity with success/completion count.
- PASS — `已归档` badge uses pale amber `#fef3c7 / #92400e`.
- PASS — `未归档` remains neutral gray.

## Carried-forward regression suite

- PASS — cached canonical account index + local all/project scope switching.
- PASS — compact archive summary + sticky action rail.
- PASS — `待处理` status semantics.
- PASS — injected JavaScript syntax.
- PASS — single selection scope + tri-state select-all.
- PASS — canonical project metadata and unknown/none distinction.
- PASS — automatic local scan + manual rescan path.
- PASS — streaming fetch -> classify -> atomic commit ordering.
- PASS — final classification matrix.
- PASS — candidate-only detail fetch.
- PASS — write -> manifest -> cleanup ordering.
- PASS — manifest-failure cleanup barrier.
- PASS — in-place METADATA_ONLY manifest-only commit.
- PASS — tracked-only cleanup preserves legacy-untracked assets.
- PASS — incomplete full-sync stop condition.
- PASS — conservative defaults 6–10s / 20 / 180–300s.
- PASS — pause/resume/cancel checkpoints.
- PASS — wall-clock batch-pause deadline and wake guard.
- PASS — live MM:SS batch-pause countdown.

## Behavioral clarification verified from implementation

Selecting a directory already performs a read-only archive scan and creates the preflight plan. Manual `重新扫描本地` is not required unless the local archive changed outside ChatHarbor or the user explicitly wants to refresh local state.

Only preflight `UNCHANGED` items avoid detail fetch. `NEW` items require detail fetch to create the archive; `VERIFY` items require detail fetch before final classification.
