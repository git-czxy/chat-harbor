# ChatHarbor Integrated Sync 0.0.7.0 — Test Report

Date: 2026-09-14

## Static/build checks

- Python patcher syntax: PASS
- Extracted integrated sync JavaScript syntax (`node --check`): PASS
- Fixed-upstream hash guard remains present: PASS
- Required runtime markers for launcher, sync, conservative policy, pause and cancel: PASS

## Planner / archive scan

- planner classification matrix: PASS
- selective-scope LOCAL_ONLY safety: PASS
- read-only archive scan duplicate/error/_files handling: PASS

## Final classification / transaction

- final classification matrix: PASS
- canonical remote-universe merge: PASS
- attachment link relocation: PASS
- candidate-only detail fetch: PASS
- write → manifest → cleanup ordering: PASS
- manifest-failure cleanup barrier: PASS
- METADATA_ONLY manifest-only commit: PASS
- tracked-only cleanup preserves legacy-untracked assets: PASS
- incomplete full-sync stop condition: PASS

## Conservative policy / runtime control

- default 6000–10000 ms request interval: PASS
- batch size 20: PASS
- 180–300 second inter-batch pause: PASS
- retry-delay normalization: PASS
- pause/resume checkpoint: PASS
- graceful cancellation checkpoint: PASS
- active-run Back-navigation guard markers: PASS
- explicit Pause/Cancel UI markers: PASS

## Boundary not reproducible in this container

The final userscript must execute against the user's actual logged-in ChatGPT browser session and File System Access API. Those browser/session conditions cannot be reproduced in this container. Real validation therefore remains limited to one integrated browser run; no additional per-Gate acceptance is required.
