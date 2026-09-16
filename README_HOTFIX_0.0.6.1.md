# ChatHarbor Integrated Sync 0.0.6.1 — Entry Visibility Hotfix

## Why this hotfix exists

The 0.0.6.0 integrated build passed planner/classifier/transaction tests, but those tests did not cover launcher/entry visibility.
A real-browser run exposed that gap.

This hotfix changes UI discoverability only. It does not redesign or reopen the validated sync core.

## Changes

1. Keep the ChatHarbor floating launcher fully visible.
   - Upstream v1.5 automatically half-hides the edge-docked launcher after 2.5 seconds.
   - ChatHarbor 0.0.6.1 disables only this automatic half-hide.
   - Dragging and edge snapping remain available.

2. Make the directory-sync route explicit in the existing UI.
   - First dialog title: `ChatHarbor｜选择空间`
   - Existing picker entry label: `选择对话 / 目录同步`
   - Picker title: `选择对话｜导出 / 本地同步`
   - No second conversation selector is introduced.

3. Add fail-closed build checks for the launcher and sync-entry markers.
   The patcher now refuses to emit a generated userscript if expected runtime/UI markers are absent.

## Build

Run:

```powershell
powershell -ExecutionPolicy Bypass -File .\prepare_clean_integrated_sync.ps1
```

Generated file:

```text
ChatHarbor-IntegratedSync-0.0.6.1.user.js
```

Before testing, disable older ChatHarbor/Gate userscripts so only this build is active.

## Expected visible path

After refreshing ChatGPT:

```text
visible floating launcher
→ ChatHarbor｜选择空间
→ 选择对话 / 目录同步
→ existing conversation picker
→ 目录预检 / 目录同步
```

The integrated sync core and safety invariants remain the same as 0.0.6.0.
