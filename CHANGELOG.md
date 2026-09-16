# ChatHarbor Changelog

## 0.0.14.1 — 2026-09-16

### First-use guidance
- When no save location is available, the Local Save card now explicitly says **第一步：选择本地保存位置** and highlights **选择位置** as the next action.
- **重新检查** is hidden until a save location exists.
- The disabled primary action now says **选择保存位置后可同步** (or asks the user to continue the previous location when permission must be restored).

### Cloud-list completion feedback
- Progressive remote loading now exposes the number already obtained while pages/projects are still loading.
- A completed remote refresh briefly shows **✓ 云端对话已加载 · 共 N 条** with a light green highlight, then returns to the normal selection count.
- The completion cue happens once per completed refresh, not once per 100-item page.

### Selection semantics fixed
- Selection is now constrained to the current visible filter/search result. Hidden items are removed from the active selection whenever the result scope changes.
- With filters active, the checkbox label becomes **全选当前结果**; without filters it remains **全选**.
- The primary sync button therefore always reflects the actual number that will be processed.

### Plain-language quick-check summary
- Removed `NEW / UNCHANGED / LOCAL_ONLY / 待核验` from the normal quick-check completion card.
- The normal card now uses only **待同步 / 已同步 / 需确认 / 异常**; technical counts remain in Details/diagnostics.

### Preserved
- No sync-engine, network-preset, Manifest, attachment, Archive Layout v2, transaction-safety, or retry-policy behavior was changed in this follow-up.

## 0.0.14.0 — 2026-09-15

### User-facing UX convergence
- Reduced the normal sync-status vocabulary to four user states: **已同步 / 待同步 / 需确认 / 异常**. Fine-grained internal states remain available to diagnostics.
- `LOCAL_UNTRACKED` is now **需确认** and is no longer auto-written by ordinary sync.
- Added stable `会话进度 X / Y` runtime progress; the current conversation and sub-task are shown separately so scheduler waits no longer hide overall progress.
- Fast-confirmed items disappear from the runtime progress once the real remote-processing phase begins and return only in the final summary.
- Simplified normal UI language and reduced repetitive row noise (`无项目` / `未归档`).

### Directory workflow
- Separated directory responsibilities: choose/change location, re-check current location, and sync selected are independent actions.
- `同步选中` no longer opens the system directory picker.
- Added IndexedDB persistence for the last FileSystemDirectoryHandle and automatic restore when browser permission remains available.

### Safer request strategy
- Replaced ambiguous speed labels with use-case presets: **少量任务（较快） / 日常使用（平衡） / 大量任务（更稳） / 保守模式（最稳）**.
- New default: 12–18s conversation-detail interval, 10 conversations/batch, 120–180s batch break.
- Attachment metadata now uses 3–5s cadence plus a 30–60s break every 10 metadata requests.
- HTTP 429 cooldown increased to 5 minutes for the first retry and 10 minutes for the second. Each observed 429 also slows detail/attachment lanes by 50% for the current page, capped conservatively.
- Advanced numeric batch/pause controls remain available under **高级设置**; the normal preset selector applies the complete preset.

### Preserved
- Archive Layout v2, Manifest authority, content-signature verification, progressive cloud discovery, lane-aware scheduler, typed HTTP retry, missing-only attachment backfill, commit-accurate state, pause/resume/cancel and tracked-only cleanup remain intact.


## 0.0.13.1 — 2026-09-15

- Classified 429, 5xx, 401/403, 404 and transport failures separately.
- Kept global 429 cooldown, but reduced ordinary 5xx retry cost with lane-specific backoff.
- Added request-context retry status for remote discovery, conversation detail and attachment metadata.
- Authentication/permission/missing-resource responses no longer enter blind retry loops.
- Preserved 0.0.13.0 lane-aware cadence, progressive discovery, Manifest convergence and attachment incrementality.

## 0.0.13.0 — 2026-09-15

### Runtime convergence
- Added one serialized backend request scheduler for ChatHarbor remote lists, project enumeration, conversation detail and attachment-metadata requests.
- Added shared HTTP 429 cooldown; API throttling now pauses the whole ChatHarbor backend-control request stream instead of allowing sibling paths to continue hitting the API.
- Added separate conservative retry handling for signed/direct attachment binary transfer without applying normal control-plane spacing to the binary payload itself.
- Removed duplicate explicit detail-loop sleeps now that cadence and batch pauses are scheduler-owned.
- Made background Remote Index refresh single-flight and sync-aware; active runs freeze their remote snapshot and defer later refresh application until completion.
- Changed visible sync state to commit-accurate semantics: classification alone can no longer display a successful synchronized state; commit failures become errors.
- Extended Manifest-first local checks to tracked attachment existence/size and made attachment reuse require physical-file validation.
- Added best-effort cleanup of newly written attachment files when Manifest commit fails.

### Preserved
- Layout v2, LOCAL_ONLY safety, convergent remote-list checkpoints, persistent Remote Index cache/fast-head refresh, missing-only attachment backfill, monotonic attachment progress, pause/resume/cancel and clean-lineage upstream pinning remain in force.

## 0.0.11.4 — 2026-09-15

### Fixed — legacy attachment convergence
- Older Manifest records with positive, internally consistent attachment evidence can now infer `complete` without another remote detail request.
- Legacy `attachment_detected = 0` remains `unknown` unless there is an explicit `attachments_checked_at` fact; zero is not silently treated as proof that no attachment exists.
- Legacy partial/failed attachment records remain retry candidates.

### Changed — missing-only attachment backfill
- Attachment-enabled sync now builds a current-reference backfill plan from `source_file_id` / sandbox identity and reuses already tracked assets.
- Only missing attachment references are downloaded. Existing matching files remain in the Manifest and are linked from regenerated Markdown.
- Cleanup continues to remove only paths no longer referenced by the committed Manifest; reused asset paths are preserved.

### Fixed — monotonic attachment progress
- Attachment progress no longer emits a pre-download and post-download count for the same file.
- The counter is completion-based: it starts from the number of reusable tracked attachments, then advances exactly once per missing attachment attempt.
- This removes the visually unstable `x / N` counter behavior observed during large attachment runs.

### Preserved
- No detail-fetch concurrency was added.
- Remote Index cache, Manifest convergence, Layout v2, conservative network policy, streaming atomic commit and LOCAL_ONLY protections are unchanged.

## 0.0.11.3 — 2026-09-15

- Fixed the release-build invariant that still expected the obsolete UI phrase `按选择范围开始流式核验与写入`, while 0.0.11.1+ runtime wording had already changed to `按实际待处理范围开始流式核验与写入`.
- This mismatch made `prepare_clean_integrated_sync.ps1` fail closed after downloading and patching the frozen upstream baseline.
- Added a regression assertion that parses `required_runtime_markers` and verifies the invariant marker follows the current runtime wording, preventing the same packaging-contract drift.
- No synchronization, Manifest, Remote Index cache, attachment, or network-policy semantics changed from 0.0.11.2.

## 0.0.11.2 — 2026-09-15

- Fixed release metadata: the 0.0.11.1 package accidentally still generated `@version 0.0.11.0`, so Tampermonkey could keep the prior runtime. 0.0.11.2 now has an explicit version bump and build-time assertion.
- Retains the 0.0.11.1 launcher fixes: `chatharbor-fab-v2`, no duplicate floating percentage/status pill, and right-rail-only runtime progress.
- Clarified that attachment-enabled transition runs may still have all selected conversations in the actionable queue when legacy attachment completeness is `unknown`; this is real attachment work, not failed Manifest fast-skip.
- No change to convergence, Remote Index cache, Layout v2, conservative network policy, or clean-lineage upstream.

## 0.0.11.1 — 2026-09-15

- Fixed stale launcher position persistence by moving ChatHarbor to the `chatharbor-fab-v2` state namespace; default position returns to the right edge.
- Removed duplicate floating-launcher progress/status during directory sync; the workspace runtime card is now the single progress display.
- Runtime sync queue now excludes entries already resolved by Manifest/preflight, while preserving their result counts. Progress numbering reflects actionable detail-fetch candidates only.
- No change to the incremental convergence, Remote Index cache, conservative network policy, Archive Layout v2, or provider lineage.

## 0.0.11.0 — 2026-09-14

### Fixed — incremental convergence
- Fixed the repeated-verification loop caused by comparing remote-list metadata against Manifest facts written primarily from the detail endpoint.
- Added dedicated `remote_list_*` observation fields and `remote_observed_at`; cheap preflight comparison now uses the same source semantics it persists.
- Added `OBSERVATION_ONLY`: a successful unchanged detail verification can advance the Manifest checkpoint without rewriting JSON/Markdown or pretending content was re-synced.
- Preserved `synced_at` as the last content/file commit timestamp during observation-only and metadata-only Manifest commits.
- Refined timestamp comparison to distinguish `same`, `different`, and `unknown` rather than treating every missing time as an ordinary difference.
- Remote merge now preserves archive/project ambiguity as `unknown` instead of collapsing conflicting known values.

### Changed — Manifest-first local planning
- Normal local scan now treats `ChatHarbor_manifest.json` as the primary local index. Manifest-tracked JSON is fast-checked by path/size instead of reparsed.
- Filesystem enumeration remains in place to discover untracked JSON and duplicate identities; missing/mismatched tracked files remain blocking errors.

### Added — attachment completeness
- Added independent attachment states: `unknown`, `none`, `complete`, `partial`, `not_downloaded`.
- Default no-download mode does not create attachment verification work.
- When attachment download is requested, incomplete/unknown records can enter `ATTACHMENT_BACKFILL` without being falsely classified as content updates.

### Added — persistent Remote Index cache
- Added IndexedDB-backed provider/account Remote Index cache for immediate reopening without blocking on a full list fetch.
- Fast refresh checks a 20-item newest window per list source. A stable head reuses the previous complete tail; any changed head falls back to a full refresh.
- Full refresh is forced at least every 24 hours. Sync requires a complete snapshot validated within 2 minutes or refreshes before starting.
- Normal `刷新` uses fast validation; Shift+`刷新` forces a complete refresh.
- Persistent cache reuse is disabled when account/workspace identity is ambiguous.

### UI / planning
- Preflight no longer forces the status filter to `待处理`; the first-stage result can visibly retain `已同步 / 新增 / 待核验` states.
- Toggling attachment download reruns preflight so attachment backfill candidates become visible before execution.

### Safety
- Remote cache remains disposable acceleration data and is not archive authority.
- Partial/head-only discovery cannot independently establish `LOCAL_ONLY`; absence decisions still require a complete remote universe.
- Existing streaming atomic commit, conservative request pacing, run-state locking, Layout v2 migration and tracked-only cleanup invariants remain in force.

## 0.0.10.1 — 2026-09-14

### Changed
- Header now keeps only the current provider context (`ChatGPT`); conversation scope remains in the scope filter and local directory context remains in the Local archive card.
- Local archive card now labels the selected root explicitly as `目录：<name>` and renames `详细信息` to `归档详情`.
- Selection statistics move to a fixed position immediately after `全选` instead of jumping between left/right edges. They show `已选 N · 共 T`, or `已选 N · 当前 M / 共 T` when the visible/filter scope is narrower than the provider universe.
- `同步内容` now mirrors the effective attachment policy in its collapsed summary: `下载附件` / `不下载附件`.

### Run-state consistency
- Network policy and attachment policy are snapshotted at sync start and remain the authoritative settings for that run.
- During an active sync, network controls and attachment controls are disabled; expanding either card shows `本次同步期间不可修改`.
- Search, scope/filter controls and per-conversation selection are also locked during the active run, preventing the visible configuration from drifting away from the executing task.
- Pause / resume / safe cancel remain available. Settings are editable again after completion or cancellation.

### Preserved
- Archive Layout v2, local-only v1→v2 migration, version-aware Planner, streaming per-conversation commit, Manifest authority, conservative network timing, MM:SS batch countdown and tracked-only cleanup are unchanged.

## 0.0.10.0 — 2026-09-14

### Added
- Introduced **Archive Layout v2** for the ChatGPT provider root: `conversations/` for non-project conversations and `projects/<project>/` for project conversations.
- Added explicit Manifest axes `provider = chatgpt` and `archive_layout_version = 2`, while retaining `conversation_id` identity inside the provider root.
- Added an explicit, resumable **Layout v1 → v2 local-only migration**. It never fetches remote conversation detail or re-downloads attachments.
- Migration copies and SHA-256 verifies tracked files, commits new Manifest paths per conversation, then removes only old Manifest-tracked paths. Untracked legacy material is preserved.
- Added migration recovery metadata so interruption after Manifest commit but before old-path cleanup can resume safely.
- Added Local archive summary counts split into project / non-project conversations.

### Changed
- New writes now target Layout v2 namespaces, removing the ambiguity between root-level project folders and conversation `_files/` folders.
- Normal synchronization is blocked while a v1 or incomplete layout migration is detected. After migration, ChatHarbor automatically runs the normal read-only Plan.
- Included the previously prepared 0.0.9.3 UI clarity changes: `当前第 X / N 条` runtime wording and a distinct pale-amber `已归档` pill.

### Extensibility
- The selected ChatGPT directory is now explicitly a provider archive root. Future providers can use sibling roots such as `claude/` or `gemini/` without changing ChatGPT's internal layout. No additional provider adapter is implemented yet.
- Globally, archive identity can be treated as `(provider, conversation_id)` while each provider Manifest keeps its native conversation identity.

### Deferred
- Source normalization / module split and removal of inherited ZIP/dead runtime code remain a separate pre-1.0 refactor after Layout v2 passes real migration smoke testing.

## 0.0.9.3 — 2026-09-14

### Changed
- Clarified per-conversation runtime progress from `同步 1 / N` to `当前第 1 / N 条`, so the number is not mistaken for a completed/succeeded counter.
- `已归档` now uses a pale amber badge (`#fef3c7` / `#92400e`); `未归档` remains neutral gray. This keeps archive state visually distinct from synchronization-status colors.

### No core behavior change
- Planner, detail verification, streaming commit, Manifest, conservative pacing, countdown, pause/resume/cancel and cleanup semantics are unchanged from 0.0.9.2.

This changelog records user-visible behavior and important runtime/safety changes. Fine-grained implementation history should remain in Git commits; GitHub Release notes can summarize each stable milestone.

## 0.0.9.2 — 2026-09-14

### Changed
- The account-level remote conversation universe is loaded once and cached in memory. Switching between `All conversations` and `Project conversations` now filters the canonical index locally instead of repeating the same remote discovery.
- Renamed the former `Personal` scope to `All conversations` because the canonical account index includes both project and non-project conversations.
- `Refresh` remains the explicit action that re-fetches remote metadata. Team/workspace data remains a separate remote universe and may require its own load.
- Renamed the aggregate sync filter from `Pending / 待同步` to `To process / 待处理`, because `VERIFY` candidates are not yet proven to require a disk write.
- Compact local archive summary now shows `Local / New / Verify` counts in one card.
- Read-only preflight completion no longer creates a separate large result card; detailed scan text is available from a small `Details` action in the local archive card.
- The right rail is split into a scrollable information area and a fixed bottom primary action, keeping `Sync selected N` visible at all times.
- Network policy and sync-content sections remain collapsed by default.

### Safety
- Canonical account-index caching does not bypass explicit `Refresh`; project/archive metadata changes become visible after refresh.
- Local archive scan / Plan remains read-only.
- Manifest, streaming atomic sync, LOCAL_ONLY protection, tracked-only cleanup, conservative pacing, pause/cancel and batch countdown invariants are unchanged.

## 0.0.9.1 — 2026-09-14

### Changed
- Inter-batch conservative pauses now show a live `MM:SS` remaining countdown (for example, `剩余 04:46`) instead of a fixed planned pause duration.
- Countdown display is derived from the existing absolute wall-clock deadline and refreshes once per second while the batch pause is active.
- No next-batch estimated clock time is shown.

### Clarified
- The 0.0.8.0 text `下一批前暂停约 N 秒` was a fixed planned pause duration, not a live countdown. The previous observation alone did not prove a standby timer failure.
- The wall-clock deadline and wake reconciliation introduced in 0.0.9.0 are retained as robustness hardening, not as a claim that such a failure had been conclusively reproduced.

## 0.0.9.0 — 2026-09-14

### Changed
- Changed version-aware sync from verify-all-then-write to per-conversation streaming `Fetch → Classify → Atomic Sync → Manifest`.
- Reduced sync scope to a single explicit selection model; removed separate `Sync filtered` and `Sync all` actions.
- Replaced `Select matches / Clear` buttons with a three-state `Select all` checkbox over the full filtered set.
- Centralized `Selected / Matched / Total` statistics on the select-all row.
- Unified the main workspace and Planner on a canonical remote index so project metadata is visible before sync planning.
- Distinguished known project / confirmed no project / unknown project membership.
- Moved archive state beside sync state as a separate low-saturation status pill; default archive filter is now `All`.
- Choosing an archive directory now automatically performs the read-only local scan and Plan; manual action is `Rescan local`.
- Added a manual remote `Refresh` action that preserves still-valid selections.

### Fixed / Hardened
- Fixed the main list showing project conversations as `No project` before Planner completion.
- Hardened conservative batch/retry waiting with absolute wall-clock deadlines so elapsed real time remains authoritative across browser throttling or system sleep.
- Added wake reconciliation and a normal request-jitter guard before network activity resumes.

### Safety
- User pause remains authoritative and never auto-resumes after system wake.
- Directory selection remains serialized after remote loading to avoid unnecessary remote/local generation concurrency.
- Existing Manifest, atomic write, LOCAL_ONLY, and tracked-only cleanup invariants remain in force.

## 0.0.8.0 — 2026-09-14

### Changed
- Introduced the Desktop-first single-page ChatHarbor workspace.
- Widened the window for 16:9 / 16:10 desktop displays.
- Moved local archive, network policy, sync content, progress and primary actions into a fixed right rail.
- Compressed search / scope / archive / sync status / time filters into the top toolbar.
- Moved preflight and sync completion reports into the right rail and localized ChatHarbor-owned reports to zh-CN / en-US.
- Restored the green right-edge draggable, snapping, half-hidden ChatHarbor launcher.

## 0.0.7.0 — 2026-09-14

### Added
- Migrated the conservative network policy to the clean lineage: six speed levels, request jitter, detail-fetch batch limit, randomized inter-batch pause, retry, pause/resume, and safe cancellation.
- Prevented normal navigation/background clicks from silently hiding an active sync task.

### Safety
- Default policy: 6–10 second request interval, 20 detail requests per batch, 180–300 second randomized batch pause.
- Cancellation stops at safe boundaries; completed per-conversation commits remain authoritative.

## 0.0.6.1 — 2026-09-14

### Fixed
- Restored launcher discoverability after the integrated build made the entry point difficult to find.
- Added build-time launcher/UI markers so a generated userscript fails closed if critical entry points disappear.

## 0.0.6.0 — 2026-09-14

### Added
- First clean-lineage integrated Version-aware Selective Sync build.
- Combined Archive Scan, Preflight Planner, content-signature classification, Manifest transactions and selective directory sync.

## Historical validated baseline

Before the integrated series, the clean-lineage reconstruction validated:

- direct directory JSON + Markdown writing;
- conversation-specific asset directories;
- Markdown local asset links;
- `conversation_id` Manifest identity;
- attachment preservation when attachment downloading is later disabled;
- non-blocking completion progress.

## 0.0.13.0 — Lane-aware Discovery Recovery

- Fixed 0.0.12.0 startup regression where list/project discovery inherited the full conservative conversation-detail delay.
- Split backend scheduling into discovery, detail and attachment-metadata lanes while retaining one global HTTP 429 cooldown.
- Added progressive root/project remote-index display and progress reporting.
- Added recoverable incomplete Remote Index cache; incomplete snapshots never prove LOCAL_ONLY and cannot start write sync.
- Exposed non-sync request/cooldown waits in loading status.
- Preserved 0.0.12.0 commit accuracy, physical asset validation, attachment rollback and active-run snapshot freeze.
