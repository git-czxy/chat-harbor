# ChatHarbor 0.0.9.0 Test Report

Date: 2026-09-14

Result: **AUTOMATED REGRESSION PASS**

Real ChatGPT + browser File System Access smoke evidence is still required before treating 0.0.9.0 as a frozen release.

## Automated tests

### Preflight Planner
PASS

- classification matrix;
- selective-scope LOCAL_ONLY safety;
- read-only archive scan duplicate/error/`*_files` handling.

### Conservative network/runtime controls
PASS

- default 6–10 second request pacing;
- batch size 20;
- randomized batch pause 180–300 seconds;
- retry delay normalization;
- pause/resume checkpoint;
- graceful cancellation checkpoint;
- active-run navigation guards.

### Version-aware sync and transaction invariants
PASS

- NEW / UPDATED / RENAMED_ONLY / UPDATED_AND_RENAMED / METADATA_ONLY / UNCHANGED classification;
- canonical remote-universe merge;
- Markdown attachment-link relocation;
- candidate-only detail fetch;
- `write → manifest → cleanup` ordering;
- Manifest-failure cleanup barrier;
- in-place METADATA_ONLY Manifest-only commit;
- tracked-only cleanup preserves legacy-untracked assets;
- incomplete full-sync safety guard;
- **streaming `fetch → classify → atomic commit` ordering**.

### Sleep / standby recovery
PASS

Synthetic wall-clock test simulates a 210-second conservative pause followed by a 2-hour OS sleep:

- expired pause is not replayed as timer ticks;
- wake path adds a normal request-jitter guard before continuing.

### UI / static integration
PASS

- injected JavaScript syntax;
- single Desktop workspace layout;
- one selection-based sync scope;
- tri-state Select All markers;
- project known / none / unknown markers;
- archive pill/default-all markers;
- automatic local scan + manual Rescan markers;
- streaming sync callbacks;
- absolute-deadline sleep + wake reconciliation markers;
- old `Sync filtered`, `Sync all`, and `Clear selection` controls absent from the current picker.

### Python patcher
PASS

`python -m py_compile ChatHarbor_IntegratedSync_patch.py`

## Core literal SHA-256

```text
8fa829172f4ac6e48c0c05c80d67df4cfe13168029f82d76d5b3aaffa55cf9ae
```

## Important test boundary

The execution environment here cannot reproduce the user's authenticated ChatGPT browser session or Windows File System Access permission state. Therefore these remain real-environment smoke checks, not simulated PASS claims:

- actual project metadata returned by current ChatGPT APIs;
- live directory picker permissions;
- visual rendering in the user's browser;
- a real sleep/wake cycle during a live sync;
- attachment network behavior against current ChatGPT URLs.
