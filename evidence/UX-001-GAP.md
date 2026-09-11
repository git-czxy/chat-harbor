# UX-001 Current-vs-Target Gap Analysis

## Confirmed current implementation

- Generic script: adapter-specific metadata uses fields such as `id`, `platform`, `title`, `createdAt`, and `updatedAt`; ChatGPT list parsing uses `item.id`, `item.title`, `create_time`, and `update_time`.
- Generic script: localStorage stores settings under `ai_exporter_settings_v1` and per-platform exported/pending ID sets under versioned keys. The export engine skips exported/pending IDs and produces per-batch ZIPs.
- Generic script: picker state includes search, export status, time field, date bounds, sorting, selected IDs, visible count, speed, batch size, attachments, and format options. It renders only a slice of the logical filtered list.
- ChatGPT v0.4: exported/pending state is stored in localStorage; list snapshots are keyed by mode/workspace and contain entries plus sync time; refresh compares a first-page sequence of `id + update_time`, then either reuses the snapshot or performs a full fetch.
- ChatGPT v0.4: project-space listing explicitly adds `projectId` and `projectTitle`; the ordinary conversation list path does not establish that archived conversations retain project metadata.

## Target gap

| Area | Current | Target | Gap |
|---|---|---|---|
| Shell | Floating button + modal/picker; ChatGPT has space-selection flow | Single desktop workspace with right rail | Large |
| Scope | ChatGPT-specific mode/workspace; generic adapters mostly expose no scope | Adapter capability with all/no/unknown/具体 scope | Large |
| Archive | ChatGPT picker has archive filter; generic model does not expose archive state | Unarchived default, explicit archive modes | Partial |
| Export state | Boolean exported/pending IDs; no reliable “has update/latest” state | Unexported/updated/latest/all, counts | Large |
| Identity | Platform + adapter `id` in memory; dedup keys use IDs | Explicit stable identity contract | Partial |
| Version | Timestamp fields and list fingerprint; no content fingerprint/revision contract | Content version signal or explicit fallback | Large |
| Selection | Set-based selection; visible slice rendered; no confirmed Shift-click | Logical-list selection with Shift-click and persistence | Partial |
| Refresh | ChatGPT cache + first-page `(id, update_time)` fingerprint; generic count cache only | Adapter incremental refresh by capability | Partial |
| Export record | Exported/pending IDs; ZIP has files but no confirmed version manifest | Versioned artifact manifest and recovery | Large |
| Progress | Batch/current/status/cancel exist in current exporters | Unified progress with success/skip/fail and resting state | Partial |

## Technical Unknowns and required verification

1. ChatGPT archived conversations and project metadata: inspect live API payloads for archived entries and project membership; current source is insufficient.
2. Stable ID source: confirmed as platform-specific adapter fields (`item.id`, `conversationId`, `session.id`, etc.); exact cross-platform contract must be formalized without assuming one field name.
3. Incremental refresh: confirmed only for ChatGPT v0.4's first-page `id + update_time` comparison; generic script has no equivalent index snapshot algorithm.
4. Exported state: confirmed as platform-scoped generic `exported/pending` ID sets and ChatGPT v0.4 localStorage ID sets; neither is a versioned artifact state.
5. ZIP/manifest: current source creates Markdown/JSON and attachment files, but no confirmed content-version manifest sufficient for recovery.
6. Reliable content-update signal: no confirmed content fingerprint or message revision; `update_time` is only a candidate signal.
7. Runtime scale/performance and all target interactions require later implementation and real-site validation.

## Readiness result

READY FOR IMPLEMENTATION PLANNING, NOT IMPLEMENTATION. No technical finding requires changing the supplied Human Decisions. The listed Unknowns must be resolved or explicitly bounded in the implementation Change before claiming completion.
