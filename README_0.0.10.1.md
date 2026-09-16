# ChatHarbor 0.0.10.1 — UI State Clarity + Run-locked Settings

This release is a focused UI/state-consistency refinement on top of the validated Archive Layout v2 build. Core synchronization and migration semantics are unchanged.

## What changed

### Information hierarchy
- Header shows only the current provider: `ChatGPT`. The conversation scope is already visible in the scope filter, and the archive directory is already visible in the Local archive card.
- Local archive displays `目录：<selected-root>` and uses `归档详情` for the detailed report action.
- Selection statistics stay at a fixed position after `全选`:
  - no narrower filter: `已选 N · 共 T`
  - narrower scope/filter: `已选 N · 当前 M / 共 T`
- `同步内容` mirrors its current result while collapsed: `下载附件` or `不下载附件`.

### Settings become run facts after Start
Before sync, network policy and attachment policy are editable. At sync start ChatHarbor takes an explicit run snapshot. During that run:

- network speed / batch size / batch-pause controls are disabled;
- attachment policy is disabled;
- search, scope/filter controls and conversation selection are disabled;
- the collapsed summaries continue to display the policy actually in force for the running task;
- expanded settings show `本次同步期间不可修改`;
- pause / resume / safe cancel remain available.

After completion or cancellation the controls become editable again. This prevents a UI change from appearing to affect a task whose runtime policy was already frozen.

## Archive Layout v2 remains unchanged

```text
chatgpt/
├─ ChatHarbor_manifest.json
├─ conversations/
└─ projects/
   └─ <project>/
```

Existing Layout v1 archives still use the local-only, resumable v1→v2 migration introduced in 0.0.10.0; migration does not re-download conversations.

## Build

```powershell
powershell -ExecutionPolicy Bypass -File .\prepare_clean_integrated_sync.ps1
```

Generated userscript:

```text
ChatHarbor-IntegratedSync-0.0.10.1.user.js
```

For the current ChatGPT archive, continue selecting the provider root itself, for example:

```text
D:\Projects\ChatHarbor\chats\chatgpt
```
