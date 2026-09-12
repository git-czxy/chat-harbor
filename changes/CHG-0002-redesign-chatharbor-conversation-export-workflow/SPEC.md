# Specification — CHG-0002

## User Outcome

Desktop users can find, filter, select, inspect status, configure an export strategy, and start an explicit export from one predictable conversation workspace without losing selections when filters change.

## Requirements

### R1 — Single workspace

The system SHALL provide one Desktop-first main page with the conversation list as the primary work area and a right-side control rail.

#### Scenario

- GIVEN a supported adapter is active
- WHEN the exporter opens
- THEN the list, compact toolbar, and control rail are available without a space-selection home page.

### R2 — Adapter-provided scope

Scope controls SHALL be supplied by the adapter. ChatGPT may expose projects/spaces; platforms without that concept SHALL hide the control. `project_id` is the internal stable key; names are display-only. “No project” and “Unknown ownership” SHALL remain distinct.

### R3 — Filters and selection

The toolbar SHALL support search, scope, archive (`unarchived` default), export status (`pending` default), and one time control. The logical filtered/sorted list SHALL be independent of rendered DOM count. Shift-click range selection SHALL use the current logical order, and filter changes SHALL preserve selected conversation identities.

### R4 — Identity and content version

Conversation identity SHALL be `platform + conversationId`; title is display-only and SHALL never be used for identity, deduplication, or version signals. Content version SHALL prefer reliable native revision, otherwise use the canonical normalized-message fingerprint, otherwise remain `null / Unknown`. Export state has exactly `never_exported`, `has_updates`, `latest`, and `unknown`; UI “待导出” is a composite filter, not a fifth state. Export artifacts represent a content-version snapshot and include platform, complete conversation ID, title-at-export, content version/fingerprint, reliable source timestamp when available, and exported-at. A title-only change SHALL not create a new conversation or content version.

### R5 — Refresh and cache

The index SHALL be cached. Default refresh SHOULD use an adapter-appropriate incremental strategy; full resynchronization SHALL remain available as a secondary action. `updatedAt / updated_at` MAY be used only as an incremental-refresh or adapter-side discovery hint. It SHALL NOT be treated as contentVersion, proof of content change, freshness, or latest, and SHALL NOT override Unknown.

### R6 — Export rail and confirmation

The rail SHALL show selected count, matched/total counts, strategy summary, record actions, and explicit actions for selected/current-filter/current-scope exports. With zero selection, the primary selected-export action SHALL be disabled and SHALL NOT silently mean “export all”. Confirmation SHALL show range, count, strategy, batch count, and whether latest records are skipped.

### R7 — Progress and recovery

Progress SHALL show total progress, batch position, current conversation, success/skipped/failed counts, current status, and cancel state. Batch pauses SHALL show “resting” and remaining pause time; ETA SHALL not be shown. Completed items remain recorded after cancellation; unfinished items SHALL not be marked exported; failed items SHALL support retry.

## Constraints

- Preserve current adapter interfaces and export contracts unless a later implementation Change explicitly specifies a compatible extension.
- Keep white background, gray borders, green primary actions, and red dangerous actions.
- Do not use ChatGPT-specific hierarchy as the universal data model.
- Do not treat user preference for “very slow” and 3–5 minute pauses as a universal default.

## Non-requirements

- ChatGPT-specific and cross-platform parity may remain partial during incremental implementation; no false parity claim is allowed.
- No provenance/license decision.
- No ChatHarbor repository/project rename.

## Acceptance Mapping

| Requirement | Acceptance Check | Evidence |
|---|---|---|
| R1–R7 | Source review + slice-specific automated/live evidence | CHG-0002 implementation evidence |
