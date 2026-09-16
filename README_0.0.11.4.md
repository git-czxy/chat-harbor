# ChatHarbor 0.0.11.4 — Attachment Incremental Convergence

This release fixes the repeated-verification loop discovered during real use and turns the existing Manifest into the primary incremental-sync index. It also adds a persistent remote-list cache with a conservative latest-window early-stop refresh.

## 0.0.11.4 attachment incremental hotfix

This release keeps the 0.0.11.x convergence/cache architecture and closes the attachment-side repetition found during real use.

### Legacy attachment-state inference

Older Manifest records that predate `attachment_state` no longer all become attachment-verification candidates. ChatHarbor now safely infers:

- `complete` only when `attachment_detected > 0`, `attachment_failed = 0`, downloaded count covers detected count, and the Manifest tracks at least that many assets;
- `partial` when positive legacy evidence shows only some attachments were downloaded or failures remain;
- `unknown` for legacy zero-count records unless an explicit `attachments_checked_at` fact exists.

This means already-complete old attachment sets can be skipped without a redundant detail fetch, while ambiguous old zeroes remain conservative.

### Missing-only backfill

When detail verification shows that attachments are incomplete, ChatHarbor now matches current attachment references against Manifest-tracked asset identities. Matching existing assets are reused; only missing references are downloaded. A 66-attachment conversation with 60 already present therefore downloads 6, not 66.

### Monotonic attachment progress

The attachment counter is completion-based. Reused assets establish the initial completed count, and each missing attachment attempt advances the counter exactly once. The UI should move monotonically, for example `60/66 -> 61/66 -> ... -> 66/66`, instead of repeatedly emitting before/after values for one item.


## 0.0.11.3 build-invariant hotfix

### Build failure fixed

0.0.11.2 could stop with:

```text
Generated runtime invariant failed; missing: 按选择范围开始流式核验与写入
```

The runtime UI had intentionally changed that phrase to `按实际待处理范围开始流式核验与写入…`, but the fail-closed build invariant retained the obsolete phrase. 0.0.11.3 updates the invariant to the current wording. Runtime sync semantics are unchanged.


- Resets the launcher persistence namespace to `chatharbor-fab-v2`, so stale top-left coordinates from earlier builds no longer override the intended right-edge default. New user drag positions persist normally after this one-time reset.
- Removes duplicate per-item percentage/status output beside the floating launcher. During a sync the launcher is still busy-locked, while the right-side runtime card is the single progress surface.
- Preflight-confirmed no-op/error/duplicate records are accounted for immediately and omitted from the runtime work queue. Runtime progress now uses only actual detail-fetch candidates as its denominator, so a plan such as `398 selected / 120 actionable` begins at `1 / 120`, not `1 / 398`.


### Important: attachment mode and the runtime denominator

The fast-skip denominator excludes only records that require no work for the current run. If `下载附件` is enabled, older Manifest records with `attachment_state = unknown` are intentionally attachment candidates. They still require one detail read to discover/backfill attachments, so a first attachment-enabled transition pass can legitimately show `1 / all selected`. With `不下载附件`, Manifest-confirmed unchanged records are omitted from the runtime queue.

This is separate from the launcher-progress bug: the duplicate launcher pill remains removed, while attachment backfill remains real work when explicitly requested.

## What this version fixes

### 1. Repeated verification now converges

The previous build could compare list metadata on the next run against metadata primarily saved from the detail endpoint. A conversation could therefore repeatedly become `VERIFY`, even after detail verification proved that its content had not changed.

0.0.11.0 introduced the separated observations, retained here:

- `remote_list_*` fields are the checkpoint used by cheap preflight comparison;
- `remote_update_time` remains the detail/source fact;
- `content_signature` remains the final content-change authority.

After a successful detail verification with unchanged content, ChatHarbor commits an `OBSERVATION_ONLY` Manifest update. The next identical run therefore reaches `UNCHANGED` without fetching the conversation detail again.

### 2. Manifest-first local scan

Normal local planning now starts from `ChatHarbor_manifest.json` instead of reparsing every tracked conversation JSON.

For Manifest-tracked conversations it performs lightweight path/size checks. Only untracked JSON is parsed. Missing or mismatched tracked files remain blocking errors rather than being silently overwritten.

This is **Manifest-first, not Manifest-only**: the archive directory is still enumerated so unexpected/untracked files are visible.

### 3. Attachment completeness is separate from content state

Attachment state is now tracked separately as:

- `unknown`
- `none`
- `complete`
- `partial`
- `not_downloaded`

With the default `不下载附件`, attachment incompleteness does not cause extra verification.

If `下载附件` is enabled and an existing record is not known to be `complete` or `none`, it becomes an attachment candidate. A verified unchanged conversation can therefore perform `ATTACHMENT_BACKFILL` without being misreported as a content update.

For older Manifest records that predate this field, attachment completeness is deliberately `unknown`; enabling attachment download can therefore cause a **one-time** attachment verification/backfill pass.

### 4. Persistent Remote Index Cache + safe early-stop

ChatHarbor now stores a disposable Remote Index cache in IndexedDB, isolated from the archive Manifest.

On open:

1. a complete cached index can render immediately;
2. ChatHarbor checks the newest remote window in the background;
3. the head window is 20 items per list source;
4. if the head fingerprint is unchanged, the previous complete tail is reused;
5. if the head changes, ChatHarbor falls back to a full remote-list refresh;
6. a full refresh is forced at least every 24 hours.

Normal `刷新` performs this fast head validation. **Shift + 刷新** forces a complete remote-index refresh.

Before sync, the executing run requires a complete remote snapshot validated within 2 minutes; otherwise it refreshes the Remote Index first. The snapshot used by the active sync is then fixed for that run.

Persistent cache is disabled when ChatHarbor cannot identify the active account/workspace unambiguously.

## State-convergence rules

This build follows these invariants:

```text
same observation -> must converge to UNCHANGED
Unknown != None != False
Remote cache != archive truth
successful verification must advance the Manifest checkpoint
content state != attachment completeness
incomplete remote universe cannot prove LOCAL_ONLY
```

See `INCREMENTAL_STATE_INVARIANTS.md` for the detailed contract.

## Existing archive compatibility

Archive Layout v2 is unchanged:

```text
chatgpt/
├─ ChatHarbor_manifest.json
├─ conversations/
└─ projects/
   └─ <project>/
```

Existing 0.0.10.x Manifest records are accepted. Because their old `remote_update_time` may contain detail-endpoint time rather than the new list-observation checkpoint, some existing records can require **one transition verification**. Once that verification commits its list observation, subsequent unchanged runs should skip detail fetch for that conversation.

If a run is cancelled during this transition, already committed conversations remain converged; the next run only needs to continue the records that have not yet advanced their checkpoint.

## Build and install

Run on Windows from the extracted package directory:

```powershell
powershell -ExecutionPolicy Bypass -File .\prepare_clean_integrated_sync.ps1
```

The build script downloads the fixed clean upstream commit, verifies the expected Git blob, and generates:

```text
ChatHarbor-IntegratedSync-0.0.11.4.user.js
```

Install/update that generated userscript in Tampermonkey.

For the current ChatGPT archive, continue selecting the provider root itself, for example:

```text
D:\Projects\ChatHarbor\chats\chatgpt
```

## First-use expectations

- First open after upgrading may perform a full Remote Index load because no persistent cache exists yet.
- Existing 0.0.10.x records can need one convergence pass as described above.
- Keep `不下载附件` if you do not want old attachment-unknown records to enter attachment verification.
- After the transition pass, an unchanged archive should show mostly `已同步`, with detail requests limited to actual candidates.

Core injected-layer SHA-256 used by the automated regression suite:

```text
bbedde8bf63d1e8c0e93b742db71d5b3b6012f8763174338be7baab4ad34ff78
```
