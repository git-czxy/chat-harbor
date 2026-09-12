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

## TASK-006B1 Cancel visibility remediation — 2026-09-12

Human Browser Verification confirmed progress/completion and normal 3/3 completion, but explicitly observed that the Cancel action was not visible during execution. This is recorded as a real TASK-006B1 Pilot interaction-state failure, not as a timing exception. The remediation makes Cancel visibility and enabled state part of the authoritative interaction model and sets explicit `running` status before the first asynchronous fetch. Human Browser Re-verification remains Pending.

## TASK-006B1 Cancel visual remediation — 2026-09-12

Human Browser Verification confirmed Cancel visibility but found insufficient visual prominence: it appeared like ordinary text without dangerous-action styling. This is recorded as a UI styling defect only; cancellation semantics are unchanged. Source and actual dist now share a red dangerous-action button contract with full width, padding, radius, white text, semibold weight, and disabled-state opacity/cursor treatment. Final visual verification remains Pending.

Local automated validation for this remediation: vertical slice tests, source/dist syntax checks, and `git diff --check` PASS. No GitHub CI claim is made.

## TASK-006B1 Human Browser Verification — PASS

Human Browser Verification confirmed the final Cancel interaction: the Cancel button was visibly red during active execution and effective when clicked. With 3 selected conversations, execution ended as `cancelled` at progress 1/3: success 1, failed 0, skipped 0, remaining 2. The started/current item completed while the remaining two items did not start, confirming cooperative cancellation. Export controls were restored after execution ended.

This is TASK-006B1 Human Browser Verification PASS only, not Human Acceptance or CHG-0002 closure. At that verification point, TASK-006B2 Retry was pending and not started; its later implementation status is recorded below.

## TASK-006B2 Retry Integration — implementation and automated verification

Capability Donor Arbitration Independent Review = PASS. The implementation reuses the generic exporter's bounded exponential retry policy (three total attempts; `2^attempt * 1000ms + 0–500ms` jitter), adapts the ChatGPT v0.4 single-refresh 401/403 behavior inside the Pilot ChatGPT adapter, and retains the current execution controller for progress, failure identities, and cooperative cancellation.

Automated/source-confirmed: immediate success does not sleep; network and 5xx errors retry within the bound; 400/404/429 do not retry; auth refresh is attempted at most once and repeated/failed authentication is terminal; cancellation blocks the next retry attempt; failure identities map only to their original targets; a new controller retries only failed targets; retry cancellation preserves completed retry work; and the actual `dist/ChatHarbor-Pilot.user.js` retry primitive is executed by the inert VM test hook. The Pilot exposes a secondary `Retry failed N` action only after a completed/cancelled execution with failures; its retry run retains the existing progress and Cancel rail.

Human Browser Verification has not been performed or claimed for TASK-006B2. No GitHub CI claim is made.

## TASK-006B2 Independent Review remediation — 2026-09-12

Independent Review found three implementation defects: (A) a cancelled failed-item retry could overwrite and drop prior failures that had not yet started; (B) a cancellation requested while an in-flight operation later failed could still trigger retry notification and backoff sleep; and (C) Pilot auth refresh was owned by the execution closure rather than the ChatGPT adapter.

The remediation adds a Core reconciliation contract that preserves unattempted prior failures, removes only successful identities, and replaces records for fresh terminal failures; unresolved identities throw and never expand to retry-all. The retry primitive checks cancellation immediately after an operation fails and again after its retry callback, so neither callback nor sleep begins after cancellation. The actual Pilot hook now exposes the same `RetryCancelledError` name/message contract and reconciliation behavior; its execution path passes the adapter-owned `refreshAuth()` seam to the retry primitive. Local tests cover both reconciliation examples, unresolved identities, cancellation-before-backoff, actual dist parity, and the adapter refresh seam. Human Browser Verification remains unclaimed.
