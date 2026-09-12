# CHG-0002 Implementation Evidence 003

Date: 2026-09-12  
Slice: TASK-006A — ChatHarbor Pilot Workspace + Selected Export Rail

## Evidence boundary

- Automated/source-confirmed: local Node tests and syntax checks listed below.
- Browser interaction: Pending Human Browser Verification; no live-site PASS is claimed.
- No GitHub CI claim is made.
- Legacy generic exporter and ChatGPT v0.4 were not modified and remain Reference-only.

## Requirement → code → test

| Requirement | Code | Automated evidence |
|---|---|---|
| ChatHarbor product workspace model | `ChatHarbor/ui/workspace.js` | `ChatHarbor/test/vertical-slice.test.js`: matched/total/selected summary and search filtering |
| Logical selection survives filtering | `ChatHarbor/ui/workspace.js` | selected identity remains after query change |
| Scope/archive are capability-aware | `ChatHarbor/core/workflow.js`, `ChatHarbor/ui/workspace.js` | ChatGPT false capabilities produce false controls |
| Zero selection cannot export all | `ChatHarbor/core/workflow.js` | selected export request is null for an empty selection |
| Explicit selected confirmation | `ChatHarbor/core/workflow.js`, `ChatHarbor/ui/workspace.js` | selected request carries selected range, count, strategy, batch count, and skip-latest |
| Pilot browser wiring | `dist/ChatHarbor-Pilot.user.js` | userscript syntax check; live execution pending Human Browser Verification |
| JSON + Markdown selected execution | `dist/ChatHarbor-Pilot.user.js` | source inspection confirms only selected IDs are fetched; live download remains pending |

## Validation

- `node ChatHarbor/test/vertical-slice.test.js` — PASS (`vertical slice PASS`)
- Node syntax checks for Core, workspace source, and Pilot userscript — PASS
- `git diff --check` — PASS

TASK-003 remains Partial/Unknown for archived project metadata; it does not block this slice because unsupported Scope/archive controls remain hidden.

## Independent Review remediation — 2026-09-12

Review found and this pass addresses:

- identity selection keys were being passed to the adapter instead of bare `conversationId`;
- Pilot export logic had drifted from the Core version/manifest contract;
- Pilot displayed `skipLatest=true` without a persisted state runtime;
- `limit=1` prevented limited multi-selection browser verification.

Independent Review round 2 found the Core helper corrected identity translation, but the Pilot distributable still passed stable identity directly to `adapter.fetchConversation`; the prior remediation was therefore incomplete. It also found that direct Pilot/Core parity assertions were missing.

Automated/source-confirmed after this remediation: the Pilot resolves selected identities through the current list and passes bare `conversationId` values only; unresolved identities abort without fallback; selected-only and zero-selection targets are directly tested; Pilot uses canonical-message fingerprint fallback and Core-shaped manifest fields with `artifactRefs: [artifactId]`; Pilot confirmation uses `skipLatest: false`; Pilot requests one conservative page of 20 records. Legacy scripts remain unchanged.

Partial Browser Evidence only: a prior Human run opened the workspace, rendered one row, and showed the zero-selection action disabled. Because this code changed afterward, selected export, multi-selection, and final browser behavior remain Pending Human Browser Verification.

## Final execution parity remediation — 2026-09-12

Independent Review found the previous parity check compared `exportConversation()` with itself and therefore did not execute Pilot logic. The test now loads the actual `dist/ChatHarbor-Pilot.user.js` in an inert Node VM hook and directly executes its `observe()` and `exportPair()` functions. The same fixture directly asserts fingerprint source/value and manifest parity, including artifact reference semantics. No browser verification is performed in this remediation.

## Human Browser Evidence and layout remediation — 2026-09-12

Human Browser Verification confirmed the real ChatGPT workspace opens, the conservative first page renders 20 conversations, matched/total is 20/20, and zero-selection state exists. It also observed horizontal list overflow and an export-selected button outside the visible viewport. These are classified as Pilot UI layout-containment defects, not Core/runtime/export-state defects.

Source and automated evidence after remediation confirms a bounded second grid row, shrinkable main/list/row/title/rail elements, vertical-only list scrolling, title ellipsis, and a flex-column rail with its action at the bottom. The test also compares the actual dist layout contract with the authoritative source contract. Final browser visual verification remains Pending Human Browser Re-verification.

## TASK-006A Human Browser Verification — PASS

Human Browser Verification confirmed: the real ChatGPT Pilot Workspace opens; the first page shows 20 conversations; prior horizontal overflow is fixed; the export-selected action remains visible; logical selection survives filtering; confirmation shows the selected range, count, strategy, and batch count; `skipLatest` is false; cancelling confirmation downloads nothing; confirming exports only the selected conversation; and that conversation produces JSON and Markdown without exporting an unselected conversation.

This is TASK-006A verification only. It is not Human Acceptance, production readiness, or CHG-0002 closure.

## TASK-006B1 Progress + Cooperative Cancellation

Automated/source-confirmed: the execution controller reports total/current/completed/success/skipped/failed/remaining/status/cancel-requested state; cancellation is cooperative and begins no new target after the in-flight target completes; completed and failed items remain recorded; failures retain identity for future retry and do not retry automatically. The Pilot rail now displays compact progress and exposes Cancel only while meaningful. TASK-006B1 live browser behavior remains Pending Human Browser Verification; TASK-006B2 Retry is not implemented.

## TASK-006B1 Single-execution remediation — 2026-09-12

Independent Review found a Pilot UI race: selection changes during an active run could re-enable Export, allowing concurrent controllers and ambiguous cancellation ownership. The Pilot now has an execution-active boundary: Export is disabled while running/cancelling, conversation checkboxes and Close are disabled, selection targets remain the pre-run snapshot, and all controls restore after completed/cancelled execution. The actual dist interaction rule is directly tested through the inert test hook. Core cancellation and failure semantics are unchanged. TASK-006B1 live browser verification remains Pending.
