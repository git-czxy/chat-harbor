---
id: CHG-0002
title: Redesign ChatHarbor conversation export workflow
type: ux
size: S2
status: VERIFYING
authority: human-owner
created: 2026-09-11
updated: '2026-09-11'
---

# CHG-0002 — Redesign ChatHarbor conversation export workflow

## Why

The current exporters expose platform-specific dialogs and controls rather than one desktop-first conversation workspace. Selection, scope, archive state, export state, refresh, strategy, and progress are not expressed as one coherent workflow.

## Current Behavior

Confirmed from source: the generic script uses a fixed floating entry button and a single overlay picker with search, export-status, time-field/date inputs, sorting, selection, format/attachment/strategy controls, and a rendered subset of the filtered list. The ChatGPT v0.4 script has a separate fixed entry button, an initial space-selection dialog, then a picker with scope, archive, export-status and time filters; it uses cached snapshots and a first-page `(id, update_time)` fingerprint for incremental refresh. Controls and state are duplicated between scripts and are not a shared Desktop-first main page.

The exact live behavior and cross-script visual parity are not re-tested in this Change because the requested scope is Discovery, Specification, and Readiness only.

## Desired Behavior

Implement a Desktop-first single main workspace: the conversation list is the primary area, a compact toolbar provides search/scope/archive/export-status/time filters, and a right control rail provides selection summary, export strategy, record management, and explicit export actions. Adapter-provided scope and stable identity/version semantics must remain platform-aware and must not encode ChatGPT's hierarchy as a universal model.

## Scope

### In

- Produce an implementation-ready specification and plan for the closed Human Decisions.
- Preserve current export behavior while introducing the target workflow in a later implementation Change phase.

### Out

- No business-code implementation in this Change.
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
- No new product decision is required by the current technical analysis; implementation may proceed only after reviewing the plan and resolving listed Unknowns where they affect correctness.

## Unknowns

- Whether archived ChatGPT conversations retain reliable project metadata is not established by the current source inspection.
- Content-version detection beyond `update_time` / platform timestamps is not established.
- Real rendered performance and interaction behavior for a large list are not validated.

## Stop Condition

This change is ready to close when all Acceptance Criteria have Evidence and required Human Acceptance is recorded.
