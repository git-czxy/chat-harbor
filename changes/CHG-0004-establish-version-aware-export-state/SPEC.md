# Specification — CHG-0004

## Discovery: Content Version Candidate Signals

Source inspection and the real ChatGPT pilot establish:

| Signal | Current evidence | Assessment |
|---|---|---|
| Message IDs | Present in `mapping[*].message.id` | Useful identity of nodes, not alone a revision |
| Current branch / leaf | Mapping `children` and selected traversal branch exist | Strong candidate when branch selection is explicit |
| Message update time | Not consistently present/verified | Candidate only |
| Conversation update time | List `update_time` exists | Change hint, not content version |
| Message count | Derivable after normalization | Weak; edits can preserve count |
| Canonical message sequence fingerprint | Computable from normalized ordered messages | Strong fallback; must be schema/versioned |
| Raw content fingerprint | Computable from preserved raw payload | Strong but sensitive to irrelevant payload noise |
| Native revision | No reliable ChatGPT field confirmed; `contentVersion` was null in real test | Unknown |

Title is excluded from every version signal.

## Version strategy candidates

1. Platform-native revision/latest leaf: highest fidelity where available, but platform-specific and currently unavailable for ChatGPT.
2. Canonical normalized message fingerprint: cross-platform and deterministic, but requires canonicalization rules and may miss raw-only changes not represented in canonical messages.
3. Hybrid: prefer native revision, otherwise canonical fingerprint; record algorithm/schema. Recommended engineering strategy when each adapter declares support.
4. Unknown fallback: when no reliable signal exists, store null and never claim Latest. This is mandatory fallback, not a fabricated version.

Readiness recommendation: implement hybrid capability-aware strategy with explicit `unknown` result. A product decision is not required because this preserves the already confirmed null semantics and does not claim freshness.

## Export State Model

```yaml
identity: platform:conversationId
currentObservedVersion: string | null
versionStatus: known | unknown
exportedVersions:
  - contentVersion: string | null
    exportedAt: timestamp
    titleAtExport: string
    representations: [json, markdown]
    manifestRef: string
lastSuccessfulExport: timestamp | null
legacyExported: boolean
```

底层事实为 `never_exported`, `has_updates`, `latest`, `unknown` freshness. UI 的“待导出”是组合筛选：`never_exported OR has_updates`，不新增第四个 UI 主状态。对于 current version null 且已有成功导出的记录，底层状态为 `unknown`（曾导出但当前新鲜度未知），不能标为 latest，也不能强制标为 has_updates。若从未导出，则进入 never_exported/pending。

## State transitions

- no export + observed known/unknown → `never_exported`.
- prior export + current known equals an exported version → `latest`.
- prior export + current known differs → `has_updates`.
- prior export + current unknown → `unknown` until fetch/version verification.
- successful export records a new artifact version; title is snapshot metadata only.
- representation regeneration with same content version adds/updates representation references and never changes conversation state.

## Manifest / recovery

Manifest schema must include `schemaVersion`, `platform`, complete `conversationId`, `titleAtExport`, `contentVersion` (nullable), `sourceUpdatedAt` (nullable and explicitly non-authoritative), `exportedAt`, `representations`, attachment metadata, and artifact references. ZIP/backup recovery matches stable identity and contentVersion, never filename/title. A null version remains null after recovery.

## Attachment semantics

Manifest metadata records user-linked conversation attachments and their identifiers, MIME type, name, and size when available. It does not prove binary download. Downloading the actual attachment remains a separate capability.
