# ChatHarbor Changelog

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
