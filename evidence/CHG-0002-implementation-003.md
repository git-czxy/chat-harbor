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
