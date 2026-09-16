# ChatHarbor Clean-lineage — Gate 4A

## Status

**IMPLEMENTED / AUTOMATED TESTS PASS / REAL BROWSER DRY-RUN PENDING**

Do **not** mark this gate PASS/FROZEN until the real archive dry-run below is accepted.

## Fixed clean lineage

- Repository: `huhusmang/ChatGPT-Exporter`
- Commit: `efa1f0f266d15c053af4ab4607b948a06332d9f7`
- Upstream version: `1.5.0`
- `Tampermonkey.js` Git blob: `3a5dfe6a696e03db7028232d45b136104e67b51f`
- Upstream userscript declares MIT.

The patcher refuses to modify a different upstream blob.

Gate 2A / 2B / 2C and Gate 3 / 3.1 remain the validated frozen baseline. This package adds a separate planner layer; it does not redesign the validated Directory Writer or Manifest commit rules.

Historical ChatHarbor v0.4/v0.5 is not an implementation source for this package.

## What Gate 4A adds

### 1. Read-only Local Archive Scan

The selected archive root is opened with File System Access API `mode: 'read'`.

The scanner:

- reads `ChatHarbor_manifest.json` if present;
- accepts only the frozen manifest contract:
  - `schema_version = 1`;
  - `identity = conversation_id`;
  - `signature_version = sha256-current_node+mapping-v1`;
- recursively finds raw conversation JSON by structure, not by title;
- indexes identity by full `conversation_id`;
- verifies tracked `json_path` identity presence;
- reports two raw conversation JSON files with the same ID as `DUPLICATE`;
- skips directories ending `_files` for conversation parsing;
- never deletes or adopts legacy assets automatically.

A raw conversation JSON that exists locally but is not manifest-tracked is visible to the planner, but is treated as **verification required**, not silently adopted as synced.

### 2. Full remote-universe preparation

`LOCAL_ONLY` is only valid if the planner has a complete remote list for the archive universe.

The upstream picker separates personal/root and project views. Gate 4A therefore complements the currently open picker with the missing **list-level** scope before planning:

- personal picker: current personal/root list + project conversation list;
- project picker: project list + personal/root list;
- team picker: upstream `listConversations(workspaceId)` already covers root + projects.

This step uses list endpoints only. It does **not** fetch conversation detail.

If complementary list enumeration fails, planning may continue for visible IDs, but:

```text
Remote universe: INCOMPLETE
LOCAL_ONLY: UNKNOWN (remote universe incomplete)
```

No local conversation is falsely classified `LOCAL_ONLY` from a partial remote scope.

### 3. Preflight classification

Gate 4A deliberately stops before content-signature verification.

Current preflight states:

- `NEW`
- `UNCHANGED`
- `VERIFY_CHANGED`
- `VERIFY_RENAMED`
- `DUPLICATE`
- `ERROR`
- `LOCAL_ONLY` (only when the remote universe is complete)

Rules:

- `conversation_id` is identity;
- title is never identity;
- title difference is detected independently of `update_time`;
- remote `update_time` is only a low-cost prefilter;
- metadata differences (`is_archived`, project ID/title) also become verification candidates;
- raw-only local conversations require verification;
- duplicate IDs are reported and excluded from automatic detail-fetch planning;
- `maximum fetch required` counts the **union** of `NEW` + verification candidates, so title/time/metadata differences do not double-count one conversation.

Final `UPDATED / RENAMED_ONLY / UPDATED_AND_RENAMED / METADATA_ONLY` remains for the next gate after detail fetch + `content_signature` comparison.

## Existing picker checkbox semantics

No second conversation selector is introduced.

- **nothing selected** -> full preflight scope;
- **one or more conversations selected** -> candidate planning is limited to those selected IDs;
- `LOCAL_ONLY` is still evaluated against the complete remote universe, not against the selected subset.

The existing Gate-3.1 directory-write test button remains because that baseline is frozen. **Do not use it during Gate-4A dry-run acceptance.**

## Build

Windows / PowerShell:

```powershell
powershell -ExecutionPolicy Bypass -File .\prepare_clean_gate4a.ps1
```

This downloads the fixed upstream file and generates:

```text
ChatHarbor-Gate4A.user.js
```

Install the generated userscript in Tampermonkey.

## Real archive dry-run acceptance

Use the real archive root that currently contains the validated `ChatHarbor_manifest.json`.

### A. Record a no-write witness before running

From the archive root in PowerShell:

```powershell
Get-FileHash .\ChatHarbor_manifest.json -Algorithm SHA256
(Get-Item .\ChatHarbor_manifest.json).LastWriteTimeUtc
```

Keep those two values.

### B. Full preflight

1. Open ChatGPT and the existing conversation picker.
2. Wait until the remote list has finished loading.
3. Leave **all conversation checkboxes unselected**.
4. Click `目录预检（全部 N）`.
5. Choose the real archive root.
6. Wait for the `DRY-RUN / READ-ONLY` report.
7. Copy the complete report back for acceptance review.

The report must contain at least:

```text
Remote
Remote universe
Scope
Local
NEW
remote-update candidates
rename candidates
UNCHANGED
metadata candidates
raw-only verify candidates
LOCAL_ONLY
duplicate IDs
ERROR
maximum fetch required
```

### C. Confirm no write

Run again:

```powershell
Get-FileHash .\ChatHarbor_manifest.json -Algorithm SHA256
(Get-Item .\ChatHarbor_manifest.json).LastWriteTimeUtc
```

Both must be unchanged.

Also confirm no conversation JSON/Markdown/`_files` path was created, renamed, or removed by the preflight action.

### D. Optional selective-planner check

After the full preflight, select a small subset in the existing picker and click `目录预检（选中 N）`.

Expected:

- `Scope` becomes the selected count (subject to valid remote IDs);
- candidate counts apply only to selected IDs;
- the full remote universe is still used for `LOCAL_ONLY` safety.

## Gate 4A stop condition

Gate 4A passes only when the real browser/local-archive dry-run shows:

- remote universe completion is `COMPLETE` (or any incomplete condition is correctly treated as unknown, never false `LOCAL_ONLY`);
- local scan completes without unintended identity collision;
- required summary counts are produced;
- no conversation detail fetch is triggered by preflight;
- manifest and archive remain byte-for-byte / timestamp unchanged by preflight;
- duplicate/error handling is conservative;
- the plan is credible enough to proceed to detail-fetch signature verification.

Only after this acceptance should development proceed to:

```text
candidate detail fetch
-> content_signature comparison
-> UPDATED / RENAMED_ONLY / UPDATED_AND_RENAMED / METADATA_ONLY
-> selective sync transaction
```
