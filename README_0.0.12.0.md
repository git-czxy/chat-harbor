# ChatHarbor 0.0.12.0 — Runtime Convergence Release

This release closes the cross-cutting runtime gaps found during real use of 0.0.11.x. It keeps the clean-lineage exporter baseline and the existing Layout v2 / Manifest model, but makes the horizontal guarantees actually cover every relevant execution path.

## What changed

### 1. One shared backend scheduler
All ChatHarbor control-plane requests to `/backend-api/` now go through one serialized scheduler:

- remote root-list discovery;
- project enumeration;
- conversation detail verification;
- attachment metadata / download-url lookup;
- legacy ChatHarbor paths that still call the inherited upstream helpers.

The selected network policy now applies to the whole ChatHarbor backend request surface rather than only conversation detail fetches.

HTTP 429 establishes a shared global cooldown. While the cooldown is active, no new ChatHarbor backend-control request is started. The runtime card distinguishes API throttling (`API 限流（429）`) from ordinary network / 5xx retry waits.

Signed/direct binary transfers use a separate data-transfer path: they do not consume normal control-plane spacing, but a 429 from the binary endpoint also raises the shared cooldown and is retried conservatively.

### 2. No duplicate per-detail delay
The old explicit detail-loop delays have been removed. Cadence, batch pauses and retries are owned by the shared scheduler, avoiding double-throttling after introducing the global gate.

### 3. Remote refresh cannot race the active run
Persistent Remote Index cache still enables immediate UI display and background head validation. The refresh is now single-flight and sync start waits for an already-running refresh before freezing the run snapshot.

Once sync begins:

- the remote snapshot is immutable for that run;
- a later refresh result is deferred instead of being applied mid-run;
- deferred remote state is applied only after the run ends, followed by a fresh read-only Preflight;
- duplicate application of the same refresh snapshot is suppressed by its validation timestamp.

### 4. `已同步` means committed, not merely classified
Classification no longer marks an actionable item as successfully synchronized before its transaction finishes.

- successful Manifest/file commit updates the visible state;
- a commit failure becomes `异常`;
- final UI state respects actual committed IDs and failed IDs.

This closes the former `Classification != Commit` drift.

### 5. Manifest-first also verifies tracked physical assets
Local planning remains Manifest-first, but tracked attachment paths are now quick-checked as physical files. Missing files or size mismatches downgrade the in-memory attachment state to `partial` so they can be repaired when attachment sync is requested.

This is still not a full-content hash audit: it is an existence/size fast check.

### 6. Attachment reuse is disk-backed
Missing-only backfill now revalidates a supposedly reusable asset against the actual filesystem immediately before reuse. If the Manifest says an attachment exists but the file is gone or its recorded size differs, it moves back into the missing set and is re-downloaded.

### 7. Failed Manifest commit cleans newly written attachment files
Newly downloaded attachment paths are tracked for the current conversation transaction. If the Manifest commit fails, those newly written attachments are removed best-effort and the in-memory Manifest record is rolled back to the prior value.

### 8. 0.0.11.4 attachment incremental behavior retained
- strong positive legacy evidence may infer `complete`;
- legacy zero counts without `attachments_checked_at` remain `unknown`;
- only missing attachments are downloaded;
- attachment progress remains monotonic and completion-based.

## Expected runtime behavior

A normal incremental run should now look like:

```text
Remote Index cache / fast refresh
        ↓
Manifest-first local Preflight
        ↓
UNCHANGED records skipped immediately
        ↓
Only candidates fetch detail
        ↓
Attachment metadata/detail/list calls share one backend scheduler
        ↓
Classify
        ↓
Commit
        ↓
Only after commit does UI show the committed result
```

If API throttling occurs:

```text
any ChatHarbor backend request -> HTTP 429
        ↓
shared global cooldown
        ↓
no new backend-control request starts
        ↓
retry after cooldown
```

## Build

```powershell
powershell -ExecutionPolicy Bypass -File .\prepare_clean_integrated_sync.ps1
```

Expected output:

```text
ChatHarbor-IntegratedSync-0.0.12.0.user.js
```

The patcher still verifies the frozen huhusmang baseline Git blob and fails closed on a different upstream file.
