# CHG-0002 Implementation Evidence 001

## Scope

First implementation slice in `通用AI对话导出脚本.txt`; no GOV-001 work and no repository rename.

## Changes

- Expanded the generic picker to a desktop-first two-column layout with the list as the main area and strategy/record controls in a right rail.
- Defaulted export status to `pending` and fixed the previous no-op `unexported` filter branch.
- Made select-all operate on the complete filtered logical list rather than only rendered rows.
- Added Shift-click range selection against the current filtered/sorted logical list.
- Added adapter-capability-gated Scope and archive controls; controls remain hidden when metadata does not provide the capability.
- Added versioned local export-record storage with stable `platform + conversationId`, title-at-export, source timestamp, exported timestamp, and `contentVersion: null` when no reliable content signal exists.

## Validation

```powershell
Get-Content -Raw '通用AI对话导出脚本.txt' | node --check --input-type=commonjs
Get-Content -Raw 'ChatGPT导出脚本（超保守版）v0.4.txt' | node --check --input-type=commonjs
git diff --check
```

Result: PASS for syntax and diff checks.

## Limitations / Unknown

- ChatGPT v0.4 still has its own initial space-selection and picker UI.
- No reliable content revision/fingerprint is available from current source; `contentVersion` intentionally remains null.
- Archived ChatGPT project metadata, live rendering, large-list performance, click behavior, downloads, and end-to-end export regression require real-site validation.

## Follow-up Verification — Main Entry Handoff

Human Owner reported that the first live test still opened the legacy `Export conversations` range modal. Source inspection confirmed `mountButton()` was calling `askChoices(adapter)` while `showConversationPicker()` was not the main entry path. The legacy modal remains as an internal compatibility function; the main entry now calls `showConversationPicker()`.

The main entry label is now `ChatHarbor`, with accessible label and tooltip `ChatHarbor · 导出对话`, and reuses the existing ChatGPT green `#10a37f` primary color. The v0.4 button and source remain unchanged as Legacy / Reference.

This follow-up is statically validated only in this session; live verification is required to confirm the click opens the new workspace.

## Spec Conformance Pass — 2026-09-11

After live feedback showed visible deviations, the generic ChatHarbor workspace was corrected without adding new product capabilities:

- Header now uses `ChatHarbor · 对话工作区` instead of exposing the platform key.
- Scope and Archive controls are present in the toolbar; adapter-provided values remain authoritative.
- Time controls are grouped under one collapsed `时间` control with field, range, and sort choices.
- Strategy controls are under `导出策略 · 调整 / 高级设置`.
- Export-history buttons are under one collapsed `导出记录` entry.
- The primary export action is in the right rail; workspace/list/rail height is constrained with internal scrolling.

Static result: PASS. Real rendering, overflow, and interaction after this pass remain Human Test Required.
