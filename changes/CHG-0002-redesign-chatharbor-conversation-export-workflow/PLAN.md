# Implementation Plan — CHG-0002

## Objective

Continue CHG-0002 incrementally on the established ChatHarbor Core + Platform Adapters architecture.

## Historical / Superseded Architecture Context

On 2026-09-11, implementation is paused pending a Base Architecture Assessment. The source comparison, capability matrix, migration costs, and recommendation are recorded in `evidence/CHG-0002-ARCH-001-BASE-ARCHITECTURE-ASSESSMENT.md`; the route selection is recorded as decision-required in `decisions/DEC-0002-base-architecture-assessment.md`.

DEC-0002 has accepted Option C. This historical spike is closed; TASK-007 remains superseded and no migration back to v0.4 is required.

## Current Baseline

ChatHarbor Core + Platform Adapters is the current architecture. The generic script and ChatGPT v0.4 are Legacy / Reference Sources. CHG-0004 version-aware export state is the current contract baseline.

## Approach

Implement in vertical slices around the Core/Adapter boundary. Do not route new product behavior through legacy UI or old full-export dialogs.

### Legacy / Current Capability Donor Arbitration

`evidence/CHG-0002-DONOR-ARBITRATION.md` is the capability-level donor matrix for ChatGPT v0.4, the generic exporter, and current ChatHarbor. Legacy / Reference means not a product route; it does not prohibit extracting a proven implementation.

Before implementing any capability:

1. inspect all available donors;
2. choose the best implementation or compatible combination;
3. prefer reuse/adaptation over rewrite;
4. rewrite only when the matrix justifies it with evidence.

Platform-specific behavior remains inside its Platform Adapter. CHG-0004 identity, version, export-state, manifest, and recovery contracts remain authoritative.

### Human Verification Strategy

Micro behavior requires automated tests and independent Review. Human Browser Verification is reserved for focused integrated workflow milestones, not repeated helper-level QA.

## Work Items

- [x] TASK-001: Complete source-based Discovery and gap analysis.
- [x] TASK-002: Specify target workflow and acceptance model.
- [ ] TASK-003: Record archived ChatGPT project metadata as source-confirmed/partial/unknown; do not block this slice unless required for correctness.
- [x] TASK-004: Define conservative adapter capability handling: show Scope/archive only when metadata fields exist; keep unknown content version as null.
- [x] TASK-005: Legacy/reference shell exists; ChatHarbor product-facing shell/integration remains incremental.
- [x] TASK-006A: Implement minimum Pilot workspace, export rail, explicit selected-export confirmation, and selected-only execution in ChatHarbor product path; Human Browser Verification PASS.
- [x] TASK-006B: Implement progress, cancellation, and retry integration.
  - [x] TASK-006B1: Progress + Cooperative Cancellation; Automated Review PASS and Human Browser Verification PASS.
  - [x] TASK-006B2: Retry; implementation, automated verification, and Independent Review PASS. Live failure-path browser evidence is deferred to an integrated workflow milestone or naturally occurring failure.
- [x] TASK-006C: Full Conversation Index + Validated Cache + Incremental Refresh; integrated browser verification found an archive-coverage gap. Personal/root archive remediation implementation, automated validation, and Independent Review PASS; focused archive browser re-verification is deferred to the layout integrated milestone.
- [ ] TASK-006D: Accepted Workspace Layout Alignment; implementation and automated validation complete, Independent Review pending.
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

Current stop condition: Independent Review of TASK-006D Accepted Workspace Layout Alignment; do not begin later CHG-0002 capabilities until Review PASS.
