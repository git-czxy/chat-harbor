---
id: CHG-0002
title: Redesign ChatHarbor conversation export workflow
type: ux
size: S2
status: VERIFYING
authority: human-owner
created: 2026-09-11
updated: '2026-09-12'
---

# CHG-0002 — Redesign ChatHarbor conversation export workflow

## Why

The current exporters expose platform-specific dialogs and controls rather than one desktop-first conversation workspace. Selection, scope, archive state, export state, refresh, strategy, and progress are not expressed as one coherent workflow.

## Current Behavior

Confirmed from source: the generic script uses a fixed floating entry button and a single overlay picker with search, export-status, time-field/date inputs, sorting, selection, format/attachment/strategy controls, and a rendered subset of the filtered list. The ChatGPT v0.4 script has a separate fixed entry button, an initial space-selection dialog, then a picker with scope, archive, export-status and time filters; it uses cached snapshots and a first-page `(id, update_time)` fingerprint for incremental refresh. Controls and state are duplicated between scripts and are not a shared Desktop-first main page.

The initial workspace and entry handoff have real-site evidence. Remaining workflow integration is being implemented incrementally under Option C; this pass is limited to export rail and explicit confirmation.

## Desired Behavior

Implement a Desktop-first single main workspace: the conversation list is the primary area, a compact toolbar provides search/scope/archive/export-status/time filters, and a right control rail provides selection summary, export strategy, record management, and explicit export actions. Adapter-provided scope and stable identity/version semantics must remain platform-aware and must not encode ChatGPT's hierarchy as a universal model.

## Scope

### In

- Implement the confirmed Desktop-first workspace workflow in incremental slices.
- Preserve current export capabilities while routing the new workflow through ChatHarbor Core/Adapters.
- TASK-006A: deliver the minimum ChatHarbor Pilot workspace, selected-export rail, explicit confirmation, and selected-only execution.

### Out

- No GOV-001 provenance/license work.
- No reopening or redesigning the closed product decisions.

## Acceptance Criteria

- [x] Discovery findings are recorded as Confirmed / Partial / Unknown / Gap.
- [x] Specification covers layout, filters, identity/version semantics, caching, strategy, confirmation, progress, cancellation, and retry behavior.
- [x] Current-vs-target gap analysis and implementation plan are recorded.
- [x] All supplied Human Decisions are referenced in DEC-0001 without changing them.
- [x] Technical Unknowns are explicit and tied to verification work.
- [x] Implementation readiness is recorded without modifying business code.

## Decisions

- `DEC-0001` records the Human Decisions supplied for this Change.
- DEC-0002 Option C is authoritative: ChatHarbor Core + Platform Adapters.
- ChatGPT v0.4 and the original generic exporter remain Legacy / Reference Sources.
- Human Resume Authorization was received on 2026-09-12; no new architecture decision is required.

## Unknowns

- Whether archived ChatGPT conversations retain reliable project metadata is not established by the current source inspection.
- Content-version detection beyond `update_time` / platform timestamps is not established.
- Real rendered performance and interaction behavior for a large list are not validated.

## Latest Implementation Note

The first live review found the new workspace visually non-conformant despite the main entry handoff. This pass corrected only the ChatHarbor generic workspace information architecture and viewport handling; the v0.4 migration remains superseded.

## Blocking Technical Spike — ARCH-001

The Change is intentionally paused after a real-site review exposed possible base-architecture coupling between the generic implementation and the mature ChatGPT v0.4 implementation. A source-based comparison of both scripts and current ChatHarbor is recorded in `evidence/CHG-0002-ARCH-001-BASE-ARCHITECTURE-ASSESSMENT.md`. No business code was changed for this spike. `DEC-0002` records that the engineering recommendation is Option C, while the route remains Human Decision Required.

## Dependency Update — 2026-09-11

DEC-0002 now accepts Option C. Architecture dependency is resolved by CHG-0003, but CHG-0002 remains BLOCKED pending independent Human Resume Authorization; its confirmed UX Specification and Decisions remain valid.

## Review Baseline — 2026-09-12

Slice 002 remediation independent Review is PASS. TASK-006A is the current implementation slice; this Change remains VERIFYING pending independent Review and Human Browser Verification. No Human Acceptance has been recorded.

## Stop Condition

This change is ready to close when all Acceptance Criteria have Evidence and required Human Acceptance is recorded.

## Current Slice — Export Rail + Explicit Confirmation

This slice is complete only when the ChatHarbor product path provides the Pilot workspace, selected-only execution, explicit confirmation, and conservative four-state/Unknown semantics. Progress, cancel, retry, cache, attachment download, and other later slices remain open.

## TASK-006A Remediation — 2026-09-12

Independent Review found identity-to-fetch translation, Pilot/Core manifest/version drift, false `skipLatest` presentation, and a one-record Pilot page boundary. The remediation keeps selection identity as `platform:conversationId`, resolves adapter fetches through ConversationMetadata, aligns Pilot output with the Core pipeline, uses `skipLatest: false` until persisted state execution exists, and requests one conservative page of at most 20 records. Status remains VERIFYING pending independent Review and Human Browser Verification; this is not Human Acceptance.

## Final Execution Remediation — 2026-09-12

The distributable execution path now resolves stable selection identities through the logical list before calling the adapter with bare conversation IDs. Direct execution-target and Core/Pilot manifest parity tests are included. Review remains the gate before any further Human Browser Verification.

## Browser Layout Remediation — 2026-09-12

Human Browser Verification confirmed workspace opening and a 20-record first page, then found horizontal list overflow and an off-viewport export action. The Pilot now constrains its second grid row and all nested flex/list children so the list scrolls internally and the export rail action remains visible. Final visual confirmation remains Pending Human Browser Re-verification after independent Review.

## TASK-006A Browser PASS / TASK-006B1 Start — 2026-09-12

TASK-006A has independent Review PASS and Human Browser Verification PASS for workspace, selection, confirmation, selected-only JSON/Markdown export, and layout containment. This is not Change closure or Human Acceptance. TASK-006B1 now adds Progress + Cooperative Cancellation only; Retry remains explicitly deferred to TASK-006B2.

## TASK-006B1 Cancel Visibility Remediation — 2026-09-12

Human Browser Verification confirmed progress/completion but found Cancel not visible during execution. Cancel is now derived from the unified execution status model, is visible before asynchronous execution begins, remains visible but disabled while cancelling, and hides only after completed/cancelled. This remains VERIFYING pending independent Review and Human Browser Re-verification.

## TASK-006B1 Cancel Visual Remediation — 2026-09-12

Human Browser Verification confirmed Cancel visibility but found it visually indistinguishable from ordinary text. The Pilot now applies the established red dangerous-action button treatment while preserving all existing Cancel state and cooperative-cancellation semantics. Review and final browser visual verification remain pending.

## TASK-006B1 Single-execution Remediation — 2026-09-12

Independent Review found that selection changes during an active Pilot execution could re-enable Export and permit a second controller. The Pilot now locks Export, conversation selection, and Close while running/cancelling, retains the execution target snapshot, and restores controls after completion or cancellation. TASK-006B1 remains VERIFYING pending independent Review and live browser verification; TASK-006B2 Retry remains pending.
