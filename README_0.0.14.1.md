# ChatHarbor 0.0.14.1 — First-use & Selection UX Follow-up

Date: 2026-09-16

This is a focused UX follow-up to 0.0.14.0. It does not change the sync engine, network presets, Manifest model, attachment logic, or transaction safety.

## 1. Clear first-use path

When no local save location is available, ChatHarbor now makes the next step explicit:

```text
本地保存
第一步：选择本地保存位置
选好后会自动检查已有文件。

[ 选择位置 ]
```

The save-location action is visually emphasized. **重新检查** stays hidden until a location actually exists.

The bottom action remains disabled and explains why:

```text
选择保存位置后可同步
```

If a previously saved directory handle exists but browser permission must be restored, the UI instead shows **继续使用**. `同步选中` never opens the directory picker implicitly.

## 2. Cloud-list loading feedback

Remote discovery remains progressive and still uses the existing paged/list APIs. During loading, the selection row exposes the amount already obtained, for example:

```text
正在加载云端对话… · 已获取 200 条
```

When the current cloud-list refresh finishes, the status line briefly changes to a light green completion notice:

```text
✓ 云端对话已加载 · 共 399 条
```

The notice disappears automatically after about 1.4 seconds. It is deliberately a brief highlight rather than a modal, toast, or repeated flash for every 100-item page.

## 3. Selection follows the current result

The visible filter/search result is now the authoritative selection scope.

Example:

```text
全部状态：399 条
筛选“待同步”：156 条
点击“全选当前结果”
→ 实际选择 156 条
→ 同步按钮显示“同步选中 156”
```

Changing search, project, archive, sync-status, or time filters removes hidden items from the active selection. There is no longer a state where the screen shows 156 matching conversations while 399 hidden conversations remain selected.

When any filter is active, the checkbox label becomes **全选当前结果**. Without filters it remains **全选**.

## 4. Quick-check summary stays user-facing

The normal progress card no longer exposes internal state names such as `NEW`, `UNCHANGED`, `LOCAL_ONLY`, or `待核验`.

It now reports only the four user-facing states when applicable:

```text
快速检查完成
待同步 156 · 已同步 242 · 异常 1
```

Technical state counts remain available in **详情 / diagnostic report**.

## 5. Preserved behavior

0.0.14.1 intentionally preserves the 0.0.14.0 engine:

- four user-facing states: 已同步 / 待同步 / 需确认 / 异常;
- stable `会话进度 X / Y` runtime display;
- directory-handle persistence and restore;
- request presets: 少量任务 / 日常使用 / 大量任务 / 保守模式;
- discovery/detail/attachment request lanes;
- global 429 cooldown and adaptive slowdown;
- typed 5xx/401/403/404 handling;
- Archive Layout v2;
- version-aware compare and content signature;
- missing-only attachment backfill;
- safe write → verify → Manifest commit → tracked-only cleanup;
- LOCAL_ONLY never auto-deleted;
- LOCAL_UNTRACKED remains a user-confirmation case;
- pause / resume / safe cancel.

## Build

```powershell
powershell -ExecutionPolicy Bypass -File .\prepare_clean_integrated_sync.ps1
```

Expected output:

```text
ChatHarbor-IntegratedSync-0.0.14.1.user.js
```

The patcher remains pinned to `huhusmang/ChatGPT-Exporter@efa1f0f266d15c053af4ab4607b948a06332d9f7` and verifies Git blob `3a5dfe6a696e03db7028232d45b136104e67b51f` before patching.
