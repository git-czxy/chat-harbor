# ChatHarbor 0.0.9.0 — Streaming Sync + Workspace Refinement

Date: 2026-09-14

Status: automated regression PASS; real ChatGPT / File System Access smoke test still required.

## Clean lineage

- Direct upstream: `huhusmang/ChatGPT-Exporter`
- Fixed commit: `efa1f0f266d15c053af4ab4607b948a06332d9f7`
- `Tampermonkey.js` Git blob: `3a5dfe6a696e03db7028232d45b136104e67b51f`
- Upstream version: `1.5.0`
- License: MIT

The patcher refuses to run if the downloaded upstream file does not match the fixed Git blob.

## What changed in 0.0.9.0

### 1. Streaming verification + atomic sync

The old integrated flow verified every detail candidate before beginning disk writes.

0.0.9.0 changes the runtime to:

```text
Read-only Plan
→ Fetch one required conversation detail
→ Classify it
→ Atomically sync it when needed
→ Manifest commit
→ Continue to the next detail candidate
```

`UNCHANGED` conversations that are already proven by remote-list metadata + Manifest still require no detail fetch.

### 2. One sync scope: Selection

There is now only one primary sync action:

```text
[ Sync selected N ]
```

`Sync filtered` and `Sync all` were removed. They are redundant because:

- filtered sync = apply filters → Select all → Sync selected;
- full sync = clear filters → Select all → Sync selected.

This also reduces the internal sync paths to one explicit set of conversation IDs.

### 3. Three-state Select All

The list now uses one standard select-all checkbox:

- unchecked: no matched conversations selected;
- checked: all matched conversations selected;
- indeterminate: some matched conversations selected.

The checkbox always acts on the complete filtered set, not only currently rendered rows.

Selection statistics are centralized on the same line:

```text
Select all    Selected N · Matched X / Total Y
```

### 4. Project metadata is loaded into the main workspace

The personal-space UI now builds the same canonical remote universe used by the Planner, merging project-space metadata by `conversation_id`.

Project state distinguishes:

- known project;
- confirmed no project;
- project membership unknown when complementary remote discovery is incomplete.

The previous behavior where the main list could display every conversation as `No project` while the Planner later knew project membership has been removed.

### 5. Archive state is a separate visual dimension

Every conversation row now shows:

- sync-state pill;
- archive-state pill.

`Active` uses a low-saturation gray pill; `Archived` uses a slightly stronger neutral gray. Archive state is no longer mixed into the metadata text line.

Default archive filter is `All` so a full local archive does not silently omit archived conversations.

### 6. Automatic read-only local scan

Normal workflow:

```text
Remote list ready
→ Choose archive directory
→ automatic read-only archive scan + Plan
```

The former `Preflight` action is now the secondary `Rescan local` action for cases where the user manually changed files on disk.

Directory selection intentionally remains disabled while the remote index is loading. This keeps initialization serial and avoids mixing stale remote generations with a newly selected local directory.

### 7. Sleep / standby recovery uses wall-clock deadlines

Batch pauses and retry waits no longer depend on decrementing one-second timer ticks.

They record an absolute deadline with `Date.now()`.

If the computer sleeps longer than the remaining pause:

- the elapsed real time counts toward the pause;
- the old pause is not replayed after wake;
- a normal request-jitter guard is inserted before the next request;
- explicit user pause remains authoritative and is never auto-resumed.

Runtime reconciliation is triggered on `visibilitychange`, `focus`, and `pageshow`.

### 8. Manual Refresh

The main header now includes `Refresh`. It reloads remote metadata, rebuilds the canonical project/archive view, and automatically rescans the selected local archive if one is already open.

Selections whose conversation IDs still exist are restored after refresh.

## Safety invariants retained

- `conversation_id` is canonical identity.
- `ChatHarbor_manifest.json` is authoritative local completion state.
- `update_time` remains a prefilter, not final content truth.
- content changes are finalized by content signature.
- write/rename ordering remains: new write → verify → Manifest commit → tracked-old-path cleanup.
- `LOCAL_ONLY` is never auto-deleted.
- untracked legacy assets are never auto-deleted.
- cooperative pause/resume/cancel remains safe-boundary based.
- default conservative policy remains 6–10s request spacing, 20 detail requests per batch, 180–300s randomized inter-batch pause.

## Build

On Windows PowerShell:

```powershell
powershell -ExecutionPolicy Bypass -File .\prepare_clean_integrated_sync.ps1
```

Expected output:

```text
ChatHarbor-IntegratedSync-0.0.9.0.user.js
```

Disable older ChatHarbor test versions before enabling this one.

## Real-environment smoke check

Use a test/copy archive first.

Verify:

1. project names are no longer all shown as `No project`;
2. archive and sync state appear as separate pills;
3. selecting a directory automatically scans it;
4. only one `Sync selected N` action exists;
5. the tri-state Select All acts on the full filtered result;
6. a small selected sync writes each conversation as it is verified instead of waiting for all detail verification to finish;
7. pause/resume/cancel still work;
8. after a system sleep longer than a batch pause, ChatHarbor does not replay the old countdown.

