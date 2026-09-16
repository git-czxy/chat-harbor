# ChatHarbor 0.0.9.1 Test Report

Date: 2026-09-14

## Scope

This is a bounded UI/runtime-feedback patch over 0.0.9.0. It adds a live inter-batch pause countdown and does not intentionally change network pacing, classification, sync scope, writer, Manifest, cleanup, pause/resume/cancel, or File System Access semantics.

## Automated validation

PASS:

- Python patcher syntax (`py_compile`).
- Injected JavaScript block syntax (`node --check`).
- Desktop workspace / single-selection-scope / tri-state-select-all markers.
- Canonical project metadata + archive-state UI markers.
- Automatic local scan / rescan markers.
- Streaming `Fetch -> Classify -> Atomic Sync -> Manifest` ordering regression.
- Planner classification matrix.
- `LOCAL_ONLY` safety and duplicate/error archive-scan regression.
- Final classification matrix: NEW / UPDATED / RENAMED_ONLY / UPDATED_AND_RENAMED / METADATA_ONLY / UNCHANGED / LOCAL_UNTRACKED / ERROR.
- Write -> Manifest -> tracked cleanup ordering.
- Manifest-failure cleanup barrier.
- Legacy-untracked asset preservation.
- Conservative defaults: 6-10s request spacing / 20 detail requests per batch / randomized 180-300s inter-batch pause.
- Pause/resume and graceful cancellation checkpoints.
- Absolute wall-clock deadline / wake reconciliation regression.
- Wake guard jitter after a simulated long suspension.
- New `MM:SS` formatter: `286000 ms -> 04:46`, `1000 ms -> 00:01`, `0 -> 00:00`.
- Batch-pause call sites opt into live countdown; old fixed `下一批前暂停约 N 秒` display text is absent from the sync core.

## Behavioral result

During a conservative inter-batch pause, the progress secondary line is now derived from the absolute pause deadline and updates approximately once per second, for example:

```text
已处理 120/395 个远端详情 · 剩余 04:46
```

No next-batch wall-clock estimate is shown.

Normal request jitter does not opt into this countdown UI.

## Evidence correction retained

The older 0.0.8.0 text `下一批前暂停约 N 秒` represented a fixed planned pause duration; its lack of visible change did not by itself prove a standby timer failure. 0.0.9.0's wall-clock deadline/wake handling is retained as robustness hardening.

## Remaining real-environment smoke evidence

A real browser run should confirm only the presentation-level behavior that cannot be fully reproduced offline:

1. enter a batch pause;
2. observe `剩余 MM:SS` decrease each second;
3. pause manually and verify the task stays paused;
4. continue and verify countdown/status resumes correctly;
5. optionally background/sleep the browser and verify the visible countdown is reconciled from wall-clock time when the page resumes.

No separate re-validation of the frozen Exporter / Directory Writer / Manifest baseline is required unless this smoke test produces contrary evidence.
