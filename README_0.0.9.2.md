# ChatHarbor 0.0.9.2 — Cached Remote Index + Compact Right Rail

Date: 2026-09-14

Status: automated regression PASS; real ChatGPT / File System Access smoke test still required.

## Clean lineage

- Direct upstream: `huhusmang/ChatGPT-Exporter`
- Fixed commit: `efa1f0f266d15c053af4ab4607b948a06332d9f7`
- `Tampermonkey.js` Git blob: `3a5dfe6a696e03db7028232d45b136104e67b51f`
- Upstream version: `1.5.0`
- License: MIT

The patcher refuses to run if the upstream file does not match the fixed Git blob.

## What changed in 0.0.9.2

### 1. One canonical account remote index

The account view now loads one complete remote universe:

```text
normal + archived conversation list
+
project conversation metadata
→ merge by conversation_id
→ canonical account index
```

The former `Personal` label is now `All conversations` because the index includes both project and non-project conversations.

Switching:

```text
All conversations ↔ Project conversations
```

is now a local in-memory filter over that canonical index and does not repeat the same remote discovery.

`Refresh` is the explicit action that re-fetches remote metadata. Team/workspace data remains a separate universe and is loaded separately when used.

### 2. `待同步` renamed to `待处理`

The preflight aggregate can contain both:

- `NEW`: definitely absent locally and requires sync;
- `VERIFY`: already exists locally and only needs content verification; it may become `UNCHANGED`.

Therefore the aggregate filter is now:

```text
待处理 = NEW + VERIFY + confirmed update/rename/metadata candidates
```

It no longer claims every candidate definitely needs a disk write.

### 3. Compact local archive card

After the automatic read-only scan, the local archive card summarizes the useful planning numbers directly, for example:

```text
Local 83 · New 312 · Verify 83
```

The previous separate large `Local scan complete` / preflight result card is removed for normal use. A small `Details` action exposes/copies the detailed diagnostic report when needed.

### 4. Primary sync action is always visible

The right rail is now structurally split:

```text
scrollable information / settings
-------------------------------
fixed bottom action
[ Sync selected N ]
```

Long archive information, progress, or reports can no longer push the primary sync action below the visible viewport.

Network policy and `Sync content` remain collapsed by default.

## Carried forward from 0.0.9.1

- streaming `Fetch → Classify → Atomic Sync → Manifest`;
- one explicit selection-based sync scope;
- tri-state Select All over the complete filtered result;
- project known / none / unknown distinction;
- separate archive-state and sync-state pills;
- automatic read-only local scan after directory selection;
- serialized remote-ready → directory-selection initialization;
- conservative pacing, retries, pause/resume and safe cancel;
- wall-clock conservative waits and wake reconciliation;
- live `MM:SS` inter-batch countdown;
- `conversation_id` identity, Manifest authority and tracked-only cleanup safety.

## Build

```powershell
powershell -ExecutionPolicy Bypass -File .\prepare_clean_integrated_sync.ps1
```

Expected output:

```text
ChatHarbor-IntegratedSync-0.0.9.2.user.js
```

Disable older ChatHarbor test versions before enabling this one.

## Real-environment smoke check

This version is well suited for immediate testing before starting a new full sync.

Confirm:

1. first load builds the full account list and project names appear where applicable;
2. switch `All conversations → Project conversations → All conversations` and confirm the switch is immediate rather than performing the long remote reload again;
3. `Refresh` still performs an explicit remote reload;
4. after choosing the archive directory, the local archive card shows `Local / New / Verify` counts and no duplicate large preflight-complete card appears;
5. the top sync filter says `待处理`, not `待同步`;
6. `Sync selected N` remains visible at the bottom of the right rail even when the information area scrolls;
7. existing batch countdown / pause / resume / cancel behavior remains intact.
