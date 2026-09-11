# Implementation Plan — CHG-0002

## Objective

Turn the closed UX decisions into an implementation-ready work package without changing business code in CHG-0002.

## Current Baseline

The generic script already has adapter metadata, localStorage settings/history, a cache-like count map, a picker, and batched export. ChatGPT v0.4 additionally has list snapshots, first-page `(id, update_time)` fingerprints, project-space listing, localStorage exported/pending state, and a separate picker. These are source-confirmed; live completeness and content-version correctness are not.

## Approach

Implement in vertical slices around a logical conversation-index model while keeping adapter-specific scope and version extraction behind adapter capabilities. The first slice is implemented in the generic exporter; the ChatGPT-specific exporter remains a separate compatibility surface until equivalent behavior is migrated and verified.

## Work Items

- [x] TASK-001: Complete source-based Discovery and gap analysis.
- [x] TASK-002: Specify target workflow and acceptance model.
- [ ] TASK-003: Verify archived ChatGPT project metadata behavior.
- [x] TASK-004: Define conservative adapter capability handling: show Scope/archive only when metadata fields exist; keep unknown content version as null.
- [x] TASK-005: Implement generic workspace shell and logical list/selection model.
- [ ] TASK-006: Implement export rail, confirmation, progress, cancellation, and retry integration in a future authorized Change.

## Risks

- Forcing project metadata or content-version fields into adapters that cannot provide them would create false state.
- Using `update_time` as content version could incorrectly classify metadata-only changes.
- Replacing two working pickers in one diff could regress export flows.

## Rollback / Recovery

Keep CHG-0002 documentation-only. Future implementation must preserve the current scripts until the new workflow has equivalent static and real-site evidence; revert by commit if acceptance fails.

## Validation

- PDR validate and unique Change ID check.
- Static source inspection for every technical Unknown.
- Later: adapter-level tests, logical-list/selection tests, syntax checks, and real-site acceptance for each supported platform.

## Stop Condition

Plan completion is not Change completion. Remaining implementation slices and live acceptance still require evidence before closure.
