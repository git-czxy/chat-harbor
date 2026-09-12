# CHG-0002 — Legacy / Current Capability Donor Arbitration

Date: 2026-09-12  
Status: Discovery / planning evidence only; no business code changed.

## Evidence rules

This arbitration compares direct source inspection of `ChatGPT导出脚本（超保守版）v0.4.txt` (A), `通用AI对话导出脚本.txt` (B), and the current `ChatHarbor/` modules (C). “Mature” below means the behavior exists in source; it is **not** a fresh runtime claim. Current Browser PASS applies only to TASK-006A and the observed portions of TASK-006B1. Unverified capabilities remain Unknown.

`updatedAt` is only a candidate-change hint. It is never selected as a content-version source. CHG-0004 remains authoritative for identity, content version, four-state export state, manifests, and known/unknown recovery.

## Donor Arbitration Matrix

| Capability | A — ChatGPT v0.4 | B — Generic exporter | C — Current ChatHarbor | Decision | Target layer | Reason / reuse work | Required automated test | Human verification needed? |
|---|---|---|---|---|---|---|---|---|
| List loading / pagination | Source-mature ChatGPT root/project/archive paging | Source-mature multi-platform adapter paging | Pilot first page only (20) | MERGE | Adapter / Index | Preserve generic adapter seam; adapt v0.4 ChatGPT pagination inside ChatGPT adapter | Page continuation, dedupe, bare ID mapping | Yes, integrated multi-page ChatGPT milestone |
| Cache | Source-mature local list snapshot | Settings/count caches only | None | ADAPT | Core Index/Cache | Extract v0.4 snapshot structure without UI; preserve scope keys | Cache read/write, stale fallback | Yes, cache/refresh milestone |
| Incremental detection | First-page `(id, update_time)` comparison | No comparable mature path | None | ADAPT | Adapter / Index | Use only as refresh hint; never feed version state | Equal/different page hints; no version-state mutation | Yes, refresh milestone |
| Selection | Mature picker selection | Mature picker selection | Logical identity selection, filter preservation, selected-only tests | KEEP_CURRENT | Core workflow / UI | Current identity and contract tests already fit Option C | Existing selection/target tests | TASK-006A PASS; no repeat now |
| Export state | Legacy exported/pending ID sets | Per-platform exported/pending history | CHG-0004 four-state, version-aware contract | KEEP_CURRENT | Core export state | Legacy sets are migration donors only | Existing CHG-0004 state tests | No, contract accepted; runtime persistence later |
| Batch | Source-mature batch limit | Source-mature batch loop + ZIP-per-batch | Not integrated | USE_GENERIC | Core execution / export sink | Generic orchestration is platform-neutral after adapter calls | Batching boundary, selected-only batches | Yes, integrated batch milestone |
| Speed / jitter | Conservative named profiles | Persistent settings + jitter factory | Not integrated | MERGE | Core strategy | Retain v0.4 profile intent; reuse generic parameter/persistence mechanics; user preference is not global default | Profile-to-delay mapping, persistence | Yes, strategy UX milestone |
| Batch pause | Source-mature 3–5 minute default | Configurable randomized pause | Not integrated | MERGE | Core strategy / execution | Reuse generic pause generator with v0.4 operational reference; do not promote personal preference to default | Pause range and cancellation boundary | Yes, pause UX milestone |
| Retry | ChatGPT detail retry + token refresh | Exponential backoff + callbacks | Deferred (TASK-006B2) | MERGE | Core retry + ChatGPT adapter | Generic backoff policy; v0.4 auth-refresh belongs in adapter | Retry limits, backoff, non-retryable auth, failure retention | Yes, retry workflow milestone |
| Cancel | Cooperative flag | `shouldContinue` loop gate | Cooperative controller + Pilot UI, Browser evidence partial | KEEP_CURRENT | Core execution / UI | Current controller has direct tests and clean ownership | Existing cancellation tests | Yes, final TASK-006B1 browser re-verification |
| Progress | Source-mature status text | Callback progress phases | Controller progress + Pilot rail | KEEP_CURRENT | Core execution / UI | Current progress model is testable and decoupled | Existing completion/failure/cancel tests | Yes, TASK-006B1 re-verification |
| Failure records | Console / batch failure behavior | Failed ID collection | Structured failure identities | KEEP_CURRENT | Core execution | Current records are retry-ready without implementing retry | Existing failure-accounting test | No until retry milestone |
| Resume | Pending/exported two-phase IDs | Pending/exported two-phase IDs | Version-aware artifact records; no execution persistence | DEFER | Export state / recovery | Requires a version-aware persisted execution contract; legacy IDs cannot prove freshness | Future resume after persisted record design | Yes, recovery/resume milestone |
| ZIP | JSZip single/batch archives | Platform-neutral `ZipSink` | JSON/Markdown pair only | USE_GENERIC | Export sink | Generic sink is the reusable multi-platform donor | ZIP contents + batch naming | Yes, download/browser milestone |
| ZIP recovery | Reads JSON IDs from ZIP, ID-only | ZIP creation; no equivalent recovery confirmed | Artifact recovery primitive, no ZIP runtime | ADAPT | Recovery | Adapt v0.4 parser to CHG-0004 identity+version/artifactId manifest contract | Known and unknown artifact recovery from ZIP manifest | Yes, recovery milestone |
| History backup / restore | JSON set backup/import | Per-platform history backup/import | CHG-0004 recovery primitive only | MERGE | Export-state persistence | Extract UI-free merge/import mechanics, but map to version-aware records | Additive merge, legacy migration, unknown preservation | Yes, backup/restore milestone |
| Attachments | ChatGPT-specific file/image retrieval | Generic `fetchAttachment` + capped downloader | Metadata normalized; no binary download | MERGE | Adapter + export sink | Keep ChatGPT endpoint behavior in adapter; reuse generic download/cap logic; metadata is not download proof | Metadata, size cap, failed download preservation | Yes, real file download milestone |
| JSON / Markdown | Mature ChatGPT renderers | Mature generic representations | Version-aware pair + manifest | MERGE | Export representations | Keep current identity/version manifest; selectively adapt generic richer renderers | Same version and identity across representations | Current pair Browser PASS; richer rendering later |
| Reasoning / sources | ChatGPT-specific extraction/rendering | Optional adapter/render format support | Capabilities false; raw retained | DEFER | Adapter capability + representations | Needs source-shape evidence and explicit canonical inclusion rules | Capability false/hide; extracted fixture if available | Yes, per-platform output milestone |
| Session / token | Session token refresh and 401/403 handling | Session/local-storage token resolution | Pilot-only ChatGPT fetch wiring | ADAPT | ChatGPT adapter | v0.4 refresh behavior is ChatGPT-specific and belongs in adapter | Token refresh single-flight / auth failure | Yes, auth-expiry workflow |
| Account ID | Workspace/account header detection | Not equivalent | Not modeled | ADAPT | ChatGPT adapter | v0.4 is sole donor; keep out of universal Core | Header only when verified workspace context exists | Yes, account/workspace validation |
| Project / workspace | ChatGPT gizmo/workspace APIs | No equivalent universal model | Capability false; TASK-003 Partial/Unknown | DEFER | ChatGPT adapter | Do not fabricate scope ownership; adapt v0.4 only after live metadata verification | Missing/known/unknown scope semantics | Yes, TASK-003 |
| Archive | ChatGPT archive/root list routes | Adapter-dependent metadata | Capability false | DEFER | ChatGPT adapter | Source evidence exists but current adapter capability remains false | Active/archived/unknown mapping | Yes, TASK-003 |
| API routes | Mature ChatGPT backend routes | Multiple platform API/DOM routes | Minimal ChatGPT routes | MERGE | Platform adapters | Generic is donor for multi-platform seams; v0.4 contributes ChatGPT-specific routes | Route fixtures and auth/header behavior | Yes, each adapter milestone |
| Platform detection / adapters | ChatGPT only | Multi-platform `resolveAdapter` and adapters | ChatGPT Adapter only | MERGE | Platform adapters | Reuse generic detection/adapters progressively; adapt each to current contract | `detect`, list, fetch, capability-negative cases | Yes, per-platform enablement |
| Picker / UI | Mature but ChatGPT-specific dialogs | Legacy picker/full-export dialog | Desktop-first workspace + Browser PASS for TASK-006A | KEEP_CURRENT | ChatHarbor UI | Current product surface matches DEC-0001; do not revive legacy UI | Existing workspace/confirmation/layout tests | TASK-006B1 re-verification only |

## Arbitration rules for implementation

Before implementing any capability:

1. inspect all available donors (A, B, and C);
2. choose the strongest implementation or a compatible combination based on source and existing evidence;
3. prefer reuse or adaptation over rewrite;
4. use `REWRITE` only when the matrix identifies no safe reusable donor and records the evidence;
5. keep platform-specific behavior within the relevant Adapter, never in universal Core or Legacy UI.

`MERGE` is intentional, not a fallback: examples include a v0.4 ChatGPT workflow algorithm behind a generic/current adapter seam, or generic retry mechanics combined with ChatGPT-specific token refresh.

## Human Verification Strategy

- Micro behavior: direct automated test plus independent Review. Human Browser Verification is not the default.
- Integrated workflow milestone: one focused Human Browser Verification after automated/review gates pass.
- Human participants are not repetitive manual QA for helper-level behavior; failed integrated evidence becomes a bounded regression with an automated guard where practical.

## Immediate effect

This is a planning control only. TASK-006B2 Retry remains prohibited. CHG-0002 remains active and awaits the independent Review / Human Browser re-verification already recorded for TASK-006B1 Cancel visual remediation.
