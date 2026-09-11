# CHG-0002 / ARCH-001 — Base Architecture Assessment

Status: Blocking Technical SPIKE; no product-route decision made.
Date: 2026-09-11

## Baseline comparison

This assessment is based on direct source inspection of `ChatGPT导出脚本（超保守版）v0.4.txt`, `通用AI对话导出脚本.txt`, and the current ChatHarbor-modified generic script. It does not treat historical plans as evidence.

The v0.4 script owns the more mature ChatGPT workflow: cached list snapshots, first-page `(id, update_time)` change detection, project-space listing, exported/pending state, ZIP recovery, batch pacing, retry, cancellation, and progress. These mechanisms are interleaved with ChatGPT-specific endpoints, workspace/project concepts, DOM assumptions, and account headers.

The generic script has a recognizable adapter seam (`resolveAdapter`, adapter `listConversations`/`fetchConversation`, capability fields) and broader platform coverage, but its original picker and full-export flow remain in the same file as adapters and export machinery. Current ChatHarbor is a partially conformed generic workspace layered onto that baseline: the entry handoff, desktop shell, logical selection, capability-gated scope/archive controls, and version-record skeleton exist, while the mature v0.4 capabilities are not yet a shared, fully verified core.

## Core coupling

Relatively platform-independent in v0.4: batch orchestration, rate/jitter and pause policy, retry/cancel/progress state, ZIP lifecycle, JSON/Markdown rendering primitives, and the conceptual exported/pending state model.

ChatGPT-coupled in v0.4: access-token/fetch interception, `/backend-api` routes, `gizmos` and workspace IDs, `ChatGPT-Account-Id`, `__NEXT_DATA__`, ChatGPT message/list shapes, project-space fallback, and the fixed entry/picker dialogs. Attachment URL resolution and some rendering are also coupled to ChatGPT response shapes.

The generic exporter has the inverse split: adapter parsing and endpoint/DOM work are platform-specific; its picker state, settings, ZIP sink, retry, batching, and history operations can become core services, but the legacy UI and default full-export UX should not be carried into that core.

## Adapter boundary

The generic adapter boundary is sufficient as a starting extraction seam: platform selection is resolved centrally and adapters expose list/fetch behavior. It is not yet a complete contract for the target product because scope/archive capability semantics, stable identity, content-version signals, attachment download versus manifest metadata, and incremental refresh are not consistently represented for every adapter. It can be moved into a recomposed Core without preserving the generic UI or old full-export entry, provided those contracts are made explicit and unsupported capabilities remain Unknown rather than fabricated.

## Capability matrix

| Capability | v0.4 | Generic | Current ChatHarbor | Platform relatedness |
|---|---|---|---|---|
| UI / picker | Mature ChatGPT picker/dialogs | Legacy picker plus current workspace | Workspace shell and entry handoff partial | High |
| Search / filter | Search, archive/time/status filters | Search/status/time; scope/archive fields | Search/status/time plus capability-gated scope/archive | Medium |
| Project / Scope | ChatGPT spaces/projects | Adapter-dependent; ordinary ChatGPT list has no project metadata | Capability-gated, incomplete for ChatGPT ordinary list | High |
| Archive | ChatGPT-specific archive/list behavior | Adapter-dependent field | UI field, platform evidence incomplete | High |
| Cache | List snapshot cache | Settings/history cache; no equivalent v0.4 snapshot confirmed | Existing generic state plus partial skeleton | Medium |
| Incremental refresh | First-page id+update_time fingerprint | No equivalent mature algorithm confirmed | Not complete | Medium/High |
| Exported state | Exported/pending ID sets | Exported/pending plus version-record skeleton | Same, `contentVersion` remains null when unavailable | Medium |
| Backup / restore | JSON backup/import | JSON backup/import | Existing generic capability | Low/Medium |
| ZIP recovery | Reads ZIPs and rebuilds exported IDs | ZIP output sink; reconstruction not confirmed | Not complete as shared workflow | Medium |
| MD / JSON | Yes | Yes | Existing export path | Low |
| Download conversation attachments | ChatGPT image/file download path | Adapter-specific attachment download | Existing capability, cross-platform parity unverified | High |
| Attachment manifest / metadata | Included through ChatGPT export metadata/records | Format/metadata options, not equivalent to download proof | Not yet a unified contract | Medium/High |
| Reasoning | ChatGPT-specific extraction/rendering | Format option/adapter data | Preserved as advanced capability, not unified | High |
| Sources | ChatGPT-specific extraction/rendering | Format option/adapter data | Preserved as advanced capability, not unified | High |
| Batch | Mature batches, default 20 | Present | Present/partially integrated | Low |
| Rate limiting | Mature base/jitter and conservative pacing | Present | Present/partially integrated | Low |
| Pause | Explicit 180–300 sec batch pause | Present strategy controls | Present but workflow integration incomplete | Low |
| Retry | Present | Present | Present in underlying path; end-to-end pending | Low |
| Cancel | Present | Present | Present in underlying path; end-to-end pending | Low |
| Progress | Present | Present | Present in underlying path; workspace integration pending | Low |
| Adapters | ChatGPT only | Multiple platform adapters | Reuses generic adapter set | High at edge, low in core |

“Download conversation attachments” means retrieving the actual user-linked image/PDF/Word/spreadsheet resources. “Attachment manifest/metadata” means recording references and attributes. The matrix does not count metadata as successful download.

## Migration cost and debt

### Option A — Generic as Core

Retention: High. Rewrite: Medium/High. Regression risk: High while old picker, old full-export path, and new workspace coexist. Multi-platform expansion: Medium. Long-term maintenance: High. Current CHG-0002 reuse: High for the shell and generic adapter seam, but limited for v0.4-specific maturity.

Debt: a mixed file/module boundary where product UX, platform adapters, legacy flow, and export state evolve together; repeated one-off migrations from v0.4 remain likely.

### Option B — v0.4 as Core

Retention: Medium/High for ChatGPT capability code. Rewrite: High for adapterization and non-ChatGPT semantics. Regression risk: High because mature ChatGPT behavior is tightly coupled to its API/DOM. Multi-platform expansion: High risk. Long-term maintenance: Medium/High. Current CHG-0002 reuse: Medium for UX concepts and selection work, low for the generic adapter path unless extracted.

Debt: ChatGPT’s workspace/project hierarchy, endpoints, and response assumptions become the de facto product model, making adapters and unsupported platforms fight the core.

### Option C — Extract & Recompose

Retention: Selective/high: retain v0.4’s proven workflow primitives and generic adapter implementations. Rewrite: High initially at the boundaries and contracts. Regression risk: Medium/High during extraction, then lower once seam tests exist. Multi-platform expansion: Lowest of the three after the boundary is established. Long-term maintenance: Medium/Low. Current CHG-0002 reuse: Medium/High for workspace/selection direction, export state skeleton, and adapter code; v0.4 remains reference for mature pipeline behavior.

Debt: an upfront extraction period and temporary dual behavior; without contract tests, the recomposed core could silently lose ChatGPT-specific capabilities.

## Recommendation

Recommend Option C — Extract & Recompose. It preserves the strongest evidence from both sources without making either legacy UI or ChatGPT’s data model the universal core. The architecture should be ChatHarbor Core (index, selection, state/version, export pipeline, pacing, retry/cancel/progress, records/recovery) plus Platform Adapters (detect, list, fetch, scope/archive capability, attachment retrieval/metadata). This is an engineering recommendation only; it does not override DEC-0001 or authorize implementation.

## Decision gate

CHG-0002 remains BLOCKED. A Human Decision is required on A, B, or C before business implementation resumes. Until then, no migration-back-to-v0.4 work is required, and v0.4 source remains preserved as Legacy/Reference.
