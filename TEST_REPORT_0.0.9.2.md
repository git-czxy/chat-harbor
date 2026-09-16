# ChatHarbor 0.0.9.2 Test Report

Date: 2026-09-14

## Scope

Bounded workspace/information-architecture refinement over 0.0.9.1. No intentional change to classification, content signature, Directory Writer, Manifest transaction order, LOCAL_ONLY protection, tracked-only cleanup, conservative pacing, pause/cancel semantics, or the 0.0.9.1 batch countdown.

## Automated validation

PASS:

- Python patcher syntax (`py_compile`).
- Injected JavaScript syntax (`node --check`).
- Cached canonical account index markers.
- Local `All conversations ↔ Project conversations` scope switching uses the cached account universe rather than calling the full remote loader again.
- Explicit `Refresh` forces a remote reload.
- `待处理 / To process` aggregate label replaces misleading `待同步 / Pending` UI wording.
- Compact archive summary derives `Verify = maximumFetchRequired - New` for preflight display.
- Preflight details are attached to the local archive card rather than rendered as a separate large result card.
- Fixed bottom `Sync selected N` action rail markers.
- Single selection scope + tri-state select-all regression.
- Canonical project metadata + known/none/unknown regression.
- Archive-state badge/default-all regression.
- Planner classification matrix.
- Read-only archive scan duplicate/error/_files handling.
- Final classification matrix.
- Streaming Fetch -> Classify -> Atomic Sync -> Manifest ordering.
- Write -> Manifest -> tracked-only cleanup ordering.
- Manifest-failure cleanup barrier.
- Legacy-untracked asset preservation.
- Conservative defaults: 6-10s request spacing / 20 detail requests per batch / randomized 180-300s pause.
- Pause/resume and safe cancellation.
- Absolute wall-clock wait deadline / wake guard regression.
- Live MM:SS batch-pause countdown regression.

## Automated test commands

```text
python tests/test_ui_092.py
node tests/test_preflight_planner.js
node tests/test_integrated_sync.js
node tests/test_conservative_policy.js
node tests/test_sleep_deadline.js
```

All PASS.

## Remaining real-environment evidence

Offline tests cannot prove ChatGPT's current project APIs, File System Access browser behavior, or visual layout on the live site. The immediate smoke test should focus on:

- project names appearing in the account index;
- all/project switching being instant after the first load;
- explicit Refresh still fetching current metadata;
- right-rail action visibility and compact preflight presentation.
