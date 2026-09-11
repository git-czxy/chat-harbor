# Implementation Plan — CHG-0002

## Objective

Turn the closed UX decisions into an implementation-ready work package without changing business code in CHG-0002.

## Current Baseline

The generic script already has adapter metadata, localStorage settings/history, a cache-like count map, a picker, and batched export. ChatGPT v0.4 additionally has list snapshots, first-page `(id, update_time)` fingerprints, project-space listing, localStorage exported/pending state, and a separate picker. These are source-confirmed; live completeness and content-version correctness are not.

## Approach

Implement later in vertical slices around a shared logical conversation-index model while keeping adapter-specific scope and version extraction behind adapter capabilities. First resolve or explicitly constrain the Unknowns below; then add the workspace shell, index/filter model, selection model, record/version model, and export/progress wiring in separate reviewable steps.

## Work Items

- [x] TASK-001: Complete source-based Discovery and gap analysis.
- [x] TASK-002: Specify target workflow and acceptance model.
- [ ] TASK-003: Verify archived ChatGPT project metadata behavior.
- [ ] TASK-004: Define adapter capability contract for scope, archive, version signal, and index refresh.
- [ ] TASK-005: Implement workspace shell and logical list model in a future authorized Change.
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

Plan completion is not Change completion. This Change is ready only for implementation planning; it does not authorize business-code edits.
