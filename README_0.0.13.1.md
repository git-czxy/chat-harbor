# ChatHarbor 0.0.13.1 — Typed Failure & Observable Retry

This release corrects the startup/discovery regression exposed by real use of 0.0.12.0. It keeps the shared correctness controls introduced in 0.0.12.0, but separates **shared control** from **shared speed**.

## What changed

### 1. One scheduler, three request lanes
All ChatHarbor `/backend-api/` control requests still share serialization, retry classification and the same global HTTP 429 cooldown, but they no longer inherit one identical cadence.

- **Discovery lane** — remote conversation lists and project enumeration: lightweight ~0.6–1.0 s cadence, no detail batch pause.
- **Detail lane** — conversation detail verification: continues to use the selected conservative speed, batch size and inter-batch pause.
- **Attachment metadata lane** — download-url / metadata lookup: controlled ~1.5–2.5 s cadence, independent from detail batch pauses.
- **Signed/direct binary transfer** remains a separate data path while still respecting a global 429 cooldown.

The network policy panel now explains that its selected speed applies to conversation detail; discovery and attachment metadata use lighter lanes.

### 2. Global 429 cooldown remains global
Any backend lane receiving HTTP 429 establishes the shared cooldown. No other ChatHarbor backend control request starts until it expires.

Ordinary network errors and HTTP 5xx retry the affected request conservatively without unnecessarily freezing every unrelated lane.

### 3. Progressive remote-index loading
A first-time/full refresh no longer behaves as a blank all-or-nothing screen.

- root active/archive pages are exposed progressively;
- after the root list is available, project complement continues in the background of the same refresh;
- project progress is reported as `项目 x/y`;
- while loading, already discovered conversations can be displayed, although write actions remain locked until the refresh reaches a stable final snapshot.

### 4. Incomplete cache is recoverable, never authoritative
When no complete cache exists, progressive/incomplete remote results may be persisted as an **incomplete UI/discovery cache**. On the next open they can be shown immediately instead of returning to a blank list.

An incomplete snapshot:

- never proves `LOCAL_ONLY`;
- never permits a write sync to begin until a complete remote snapshot is available;
- is automatically refreshed again because `complete != true`.

An existing complete cache is never replaced by a progressive incomplete snapshot during a refresh.

### 5. Loading waits are observable
When discovery is waiting on normal lane cadence or a global 429 cooldown, the list status reports the current reason. A 429 cooldown shows a live remaining duration instead of appearing frozen on `正在加载列表…`.

### 6. 0.0.12.0 correctness guarantees retained
This release keeps:

- Manifest convergence / observation checkpoints;
- Manifest-first local indexing with physical asset checks;
- missing-only attachment backfill;
- commit-accurate visible state (`classified != committed`);
- background refresh single-flight and active-run snapshot freeze;
- attachment rollback on failed Manifest commit;
- Layout v2 migration safety.

## Expected startup behavior

With a usable cache:

```text
Open ChatHarbor
→ show cached remote index immediately
→ lightweight head validation
→ stable head: stop
→ changed head: full refresh
```

Without a cache:

```text
Open ChatHarbor
→ root list pages arrive progressively
→ root conversations become visible
→ project complement progresses
→ complete remote snapshot is cached
```

A full discovery must no longer use the 6–10 second conversation-detail cadence for every list/project request.


## Typed HTTP failure handling

0.0.13.1 keeps the lane-aware scheduler from 0.0.13.0, but makes retry behavior depend on the actual failure class and request lane:

- `429`: shared global cooldown, unchanged;
- `500-599`: service-side failure with bounded lane-specific retry;
- `401/403`: authentication / permission failure, no blind retry loop;
- `404`: missing remote resource, no blind retry loop;
- fetch/transport exception: network-connection retry with lane-specific backoff.

The runtime status now includes request context. Examples:

```text
服务端错误（HTTP 500）
对话详情 · 退运邮件清点系统… · 第 1/2 次重试前

服务端错误（HTTP 503）
附件元数据 · report.zip · 第 1/2 次重试前
```

5xx retry costs are intentionally lower than 0.0.13.0:

- discovery: 5s, 10s;
- conversation detail: 15s, 30s;
- attachment metadata: 5s, 10s;
- signed/direct binary transfer: 10s, 20s.

A final failed request is handed back to its owning operation so one bad conversation or attachment is recorded and the run can continue.

## Build

```powershell
powershell -ExecutionPolicy Bypass -File .\prepare_clean_integrated_sync.ps1
```

Expected output:

```text
ChatHarbor-IntegratedSync-0.0.13.1.user.js
```

The patcher still verifies the frozen huhusmang baseline Git blob and fails closed on a different upstream file.
