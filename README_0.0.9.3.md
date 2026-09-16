# ChatHarbor 0.0.9.3 — UI Clarity Hotfix

This is a bounded UI-only hotfix over 0.0.9.2.

## Changes

- Runtime phase text now says `当前第 X / N 条 · 阶段` instead of `同步 X / N · 阶段`. `X / N` is the current item ordinal in the selected plan, not a success counter.
- `已归档` uses a pale amber badge; `未归档` remains neutral gray.

## Important behavior clarification

Selecting a directory already triggers a read-only local scan and preflight plan. If the archive summary says, for example, `本地 83 · 新增 312 · 待核验 83`, a separate manual `重新扫描本地` is not required. `重新扫描本地` is for files changed outside ChatHarbor or an explicit refresh of local state.

`NEW` conversations require detail fetch because they must be written. `VERIFY` conversations also require detail fetch before final classification. Only preflight `UNCHANGED` entries skip detail fetch.

## Build

```powershell
powershell -ExecutionPolicy Bypass -File .\prepare_clean_integrated_sync.ps1
```

Generated userscript:

```text
ChatHarbor-IntegratedSync-0.0.9.3.user.js
```
