# ChatHarbor 0.0.14.0 — Automated Regression Report

Date: 2026-09-15

Status: **AUTOMATED REGRESSION PASS**

A real ChatGPT endpoint smoke test is still required for live rate-limit behavior and final Windows userscript generation. Private `/backend-api/` rate-limit thresholds are not public, so automated tests can verify scheduling semantics but cannot prove that HTTP 429 will never occur.

## New 0.0.14.0 contracts checked

### User-facing state convergence

- main UI exposes `已同步 / 待同步 / 需确认 / 异常`;
- technical states such as `仅元数据 / 本地未跟踪 / 内容更新 / 仅改名 / 待核验` do not appear as main picker statuses;
- `LOCAL_UNTRACKED` requires user confirmation and is not an ordinary final auto-write action.

### Stable progress

- runtime progress has a fixed `会话进度 X / Y` denominator;
- current conversation is displayed separately;
- attachment / save / retry sub-actions do not replace main progress;
- fast-confirmed conversations do not inflate the runtime work denominator.

### Directory action separation

- sync no longer invokes the system directory picker;
- only choose/change-directory invokes `showDirectoryPicker`;
- the prior directory handle is stored/restored through IndexedDB;
- re-check works only on the current directory;
- sync is disabled until a save location exists.

### Request strategy

- default preset: 12–18 s detail interval, 10 conversations/batch, 120–180 s break;
- discovery cadence: 1.0–1.5 s;
- attachment metadata cadence: 3–5 s;
- attachment metadata micro-batch: 10 requests followed by 30–60 s random break;
- HTTP 429 cooldown: 5 minutes for the first retry and 10 minutes for the second;
- each 429 increases detail/attachment pacing by 50% for the current page (capped);
- 5xx remains bounded and lane-specific;
- 401/403/404 do not enter blind retry loops.

### User-language UI

- request presets use `少量任务（较快） / 日常使用（平衡） / 大量任务（更稳） / 保守模式（最稳）`;
- advanced batch/pause controls are nested under `高级设置`;
- main UI uses `本地保存 / 重新检查 / 请求速度 / 附件 / 搜索对话或项目`;
- short tooltips are present only where useful;
- normal rows suppress repetitive `无项目 / 未归档` noise.

## Existing regressions retained

The following suites also pass:

- Layout v1 → v2 local-only migration and idempotence;
- byte-identical JSON / Markdown / tracked asset migration;
- untracked legacy asset preservation;
- planner classification matrix and LOCAL_ONLY safety;
- candidate-only detail fetch;
- streaming fetch → classify → atomic commit;
- Manifest-failure cleanup barrier;
- METADATA_ONLY / OBSERVATION_ONLY manifest-only commit;
- repeated-verification convergence;
- attachment completeness separation;
- missing-only attachment backfill;
- pause / resume / cancel;
- wall-clock wait and wake guard behavior;
- injected JavaScript syntax checks.

## Build contract

The PowerShell builder:

1. downloads the frozen huhusmang `Tampermonkey.js` at commit `efa1f0f266d15c053af4ab4607b948a06332d9f7`;
2. verifies Git blob `3a5dfe6a696e03db7028232d45b136104e67b51f`;
3. applies the ChatHarbor 0.0.14.0 patcher;
4. fails closed if required runtime markers are missing.

Expected output:

```text
ChatHarbor-IntegratedSync-0.0.14.0.user.js
```
