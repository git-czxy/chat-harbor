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
