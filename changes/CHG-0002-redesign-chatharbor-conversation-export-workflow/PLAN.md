# Implementation Plan — CHG-0002

## Objective

Turn the closed UX decisions into an implementation-ready work package without changing business code in CHG-0002.

## Blocking Technical Spike — ARCH-001

On 2026-09-11, implementation is paused pending a Base Architecture Assessment. The source comparison, capability matrix, migration costs, and recommendation are recorded in `evidence/CHG-0002-ARCH-001-BASE-ARCHITECTURE-ASSESSMENT.md`; the route selection is recorded as decision-required in `decisions/DEC-0002-base-architecture-assessment.md`.

No UI or business-code work may continue until a Human Decision selects Option A, B, or C. This spike does not reopen DEC-0001. TASK-007 remains superseded: migration of the new workspace back into ChatGPT v0.4 is not required; v0.4 remains Legacy / Reference.

## Current Baseline

The generic script is the ChatHarbor primary implementation. ChatGPT v0.4 additionally has list snapshots, first-page `(id, update_time)` fingerprints, project-space listing, localStorage exported/pending state, and a separate picker; it is now Legacy / Reference only. These are source-confirmed; live completeness and content-version correctness are not.

## Approach

Implement in vertical slices around a logical conversation-index model while keeping adapter-specific scope and version extraction behind adapter capabilities. The first slice is implemented in the generic exporter; the ChatGPT-specific exporter remains a separate compatibility surface until equivalent behavior is migrated and verified.

## Work Items

- [x] TASK-001: Complete source-based Discovery and gap analysis.
- [x] TASK-002: Specify target workflow and acceptance model.
- [ ] TASK-003: Verify archived ChatGPT project metadata behavior for ChatHarbor's ChatGPT adapter.
- [x] TASK-004: Define conservative adapter capability handling: show Scope/archive only when metadata fields exist; keep unknown content version as null.
- [x] TASK-005: Implement generic workspace shell and logical list/selection model.
- [ ] TASK-006: Implement remaining export rail, confirmation, progress, cancellation, and retry integration in ChatHarbor.
- [x] TASK-007: Supersede migration of the new workspace into ChatGPT v0.4; retain v0.4 as Legacy / Reference.

## Risks

- Forcing project metadata or content-version fields into adapters that cannot provide them would create false state.
- Using `update_time` as content version could incorrectly classify metadata-only changes.
- Replacing two working pickers in one diff could regress export flows.

## Rollback / Recovery

Keep ChatGPT v0.4 unchanged as Legacy / Reference. Future ChatHarbor implementation must preserve working export capabilities until equivalent evidence exists; revert by commit if acceptance fails.

## Validation

- PDR validate and unique Change ID check.
- Static source inspection for every technical Unknown.
- Later: adapter-level tests, logical-list/selection tests, syntax checks, and real-site acceptance for each supported platform.

## Stop Condition

Plan completion is not Change completion. Remaining implementation slices and live acceptance still require evidence before closure.

Current stop condition: remain BLOCKED until the architecture route is selected; then revise only the affected implementation plan before resuming.
