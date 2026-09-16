# ChatHarbor 0.0.14.0 — User-facing UX Convergence

Date: 2026-09-15

This release keeps ChatHarbor's detailed internal sync semantics, but simplifies what ordinary users need to see and decide. It also makes the request strategy more conservative after real-world HTTP 429 observations during large attachment-bearing syncs.

## 1. Four user-facing states

The main conversation list now exposes only four states:

- **已同步** — nothing to do.
- **待同步** — the next action is simply sync.
- **需确认** — ChatHarbor should not decide automatically; review first.
- **异常** — something failed or conflicts and needs attention.

Fine-grained internal states such as NEW, VERIFY_CHANGED, RENAMED_ONLY, METADATA_ONLY, ATTACHMENT_BACKFILL and LOCAL_UNTRACKED remain available to diagnostics, but no longer become primary UI vocabulary.

Important behavioral boundary: `LOCAL_UNTRACKED` is no longer auto-written by an ordinary sync. It is user-facing **需确认**.

## 2. Stable session progress

During the real network-processing phase, the progress card keeps one stable meaning:

```text
会话进度 58 / 302 · 19%

当前：某个会话
正在获取对话 · 8 秒后继续
```

The denominator is frozen when the runtime work queue starts. Fast-confirmed conversations, pre-known errors, and items requiring user confirmation are not mixed into this denominator. A conversation increments the numerator once it reaches a terminal result, including a final failure.

Attachment activity stays below the session progress, for example:

```text
当前：某个会话
正在下载附件 · 16 / 66
```

Transient scheduler waits no longer replace or gray out the main session progress.

## 3. Clear directory responsibilities

The three local-save actions now have separate responsibilities:

- **选择 / 更换目录** — the only action that opens the system directory picker.
- **重新检查** — re-checks the current save location only.
- **同步选中** — performs sync only; it no longer silently asks for a directory.

ChatHarbor stores the last `FileSystemDirectoryHandle` in IndexedDB. On reopen it attempts to restore the previous location automatically. If browser permission requires a new user gesture, the button becomes **继续使用** instead of making sync itself open a directory picker.

## 4. Plain-language UI

Normal UI now prefers user language over implementation language:

- 本地保存
- 重新检查
- 请求速度
- 附件
- 搜索对话或项目
- 正在获取对话
- 正在下载附件
- 服务器暂时出错
- 请求过多，暂时休息

Technical terms such as Manifest, Remote Index, Preflight, layout internals, request lanes and commit details remain in diagnostics / detailed reports rather than the normal workflow.

Normal rows are quieter: `无项目` and `未归档` are not repeated on every conversation. Project names and `已归档` appear only when they add useful information.

## 5. Request-speed presets

The old speed labels were ambiguous. 0.0.14.0 changes the preset names to use-case language and applies the whole preset (conversation interval + batch size + batch break) together.

| Preset | Conversation interval | Batch | Break between batches | Suggested use |
|---|---:|---:|---:|---|
| **少量任务（较快）** | 4–7 s | 15 | 60–90 s | Small one-off syncs |
| **日常使用（平衡）** | 8–12 s | 12 | 90–120 s | Normal incremental use after the archive has converged |
| **大量任务（更稳）** | 12–18 s | 10 | 120–180 s | Default; large catch-up runs |
| **保守模式（最稳）** | 18–25 s | 8 | 180–300 s | Recommended after a `请求过多` / HTTP 429 event |

The built-in default is **大量任务（更稳）**.

For a run like the current real-world case — roughly 398 selected conversations, attachment download enabled, and HTTP 429 already observed — use **保守模式（最稳）** for the remainder of the large catch-up. After the archive converges and normal runs involve only a small number of changed conversations, switch to **日常使用（平衡）**.

These values reduce request pressure; they cannot guarantee that private ChatGPT backend rate limiting or anti-abuse systems will never respond with 429 because those thresholds are not publicly specified.

### Hidden safety behavior

Normal users do not need to configure the following separately:

- cloud-list discovery: about 1.0–1.5 s cadence;
- attachment metadata: about 3–5 s cadence;
- every 10 attachment-metadata requests: additional random 30–60 s break;
- first HTTP 429: global 5-minute cooldown;
- second retry after 429: global 10-minute cooldown;
- each observed 429 increases the current page's detail/attachment pacing by about 50%, capped conservatively.

Signed/direct attachment binary transfer remains a separate data path but still respects a global 429 cooldown.

## 6. Error wording

Main UI messages are action-oriented:

```text
服务器暂时出错（500）
15 秒后重试
```

```text
请求过多，暂时休息
稍后自动继续
```

Request type, endpoint class, HTTP code, retry attempt and internal scheduler details remain available in detailed diagnostics.

## 7. Core sync behavior retained

This UX convergence does **not** remove or weaken the existing internal correctness model:

- conversation_id identity;
- content-signature final verification;
- Manifest convergence / observation checkpoints;
- Archive Layout v2;
- safe write → verify → Manifest commit → tracked-only cleanup ordering;
- LOCAL_ONLY never auto-delete;
- duplicate/error blocking;
- missing-only attachment backfill;
- commit-accurate visible state;
- background remote refresh single-flight;
- progressive cloud-list loading;
- incomplete cloud list cannot prove absence or start an unsafe full write sync;
- typed HTTP retry handling;
- pause / resume / safe cancel.

## Build

```powershell
powershell -ExecutionPolicy Bypass -File .\prepare_clean_integrated_sync.ps1
```

Expected output:

```text
ChatHarbor-IntegratedSync-0.0.14.0.user.js
```

The patcher remains pinned to `huhusmang/ChatGPT-Exporter@efa1f0f266d15c053af4ab4607b948a06332d9f7` and verifies Git blob `3a5dfe6a696e03db7028232d45b136104e67b51f` before patching.
