# CHG-0002 Implementation Evidence — Slice 002

## Resume authorization

Human Resume Authorization was received on 2026-09-12 in the main governance conversation: CHG-0002 may resume under authoritative DEC-0002 Option C. This is authorization evidence, not a new product decision.

## Slice

Export Rail + Explicit Export Confirmation. The generic script's current ChatHarbor workspace now exposes selected-only primary export; the old “export all” action is not wired as the primary selected action. Confirmation model fields are `range`, `count`, `strategy`, `batchCount`, and `skipLatest`.

## Evidence classification

- Source/code confirmed: selected-only handler rejects zero IDs; confirmation includes the five required fields; green primary action and existing workspace remain.
- Automated-test confirmed: confirmation model shape; selection identities survive filter-model changes; existing Core vertical-slice and version-state tests pass.
- Automated-test confirmed: four-state status helper preserves `never_exported`, `latest`, `has_updates`, and `unknown`; Unknown is not treated as latest/skippable.
- Automated-test confirmed: zero-selection confirmation is not produced; selected-only confirmation contains range, count, strategy, batchCount, and skipLatest.
- Local syntax confirmed: `ChatHarbor/core/workflow.js` and current generic userscript syntax pass.
- Live-site confirmed: prior workspace entry/list behavior only; this slice's browser interaction is not yet Human-verified.
- Unknown: production UI, actual export run integration, full four-state UI rendering, and TASK-003 archived project metadata live behavior.

No GitHub CI result is claimed.
