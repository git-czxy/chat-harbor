# ChatHarbor 0.0.8.0 Automated Regression Report

Date: 2026-09-14

## Result

**PASS — automated regression / static integration**

真实 ChatGPT 页面视觉与 File System Access 仍属于真实环境 smoke evidence，不在离线测试中伪造 PASS。

## Core regression

执行：

- `node tests/test_preflight_planner.js`
- `node tests/test_integrated_sync.js`
- `node tests/test_conservative_policy.js`

通过项：

- Planner classification matrix
- selective-scope LOCAL_ONLY safety
- read-only archive scan duplicate/error/_files handling
- final classification matrix
- canonical remote-universe merge
- attachment-link relocation
- candidate-only detail fetch
- write → manifest → cleanup ordering
- manifest-failure cleanup barrier
- METADATA_ONLY manifest-only commit
- tracked-only cleanup preserves legacy-untracked assets
- incomplete full-sync stop condition
- conservative defaults: 6–10s / 20 / 180–300s
- policy normalization + retry delays
- pause/resume checkpoint
- graceful cancel checkpoint
- active-run navigation guards

## Core immutability check

0.0.7.0 与 0.0.8.0 的 `directory_writer` literal 完全一致：

```text
f4c01a1e3c2f94e3572fe76d1263f0c4ab3ea29a3c64b121482b6b2eab6122cc
```

这证明本轮 UI 改造没有改动同步 Core literal。

## UI regression

执行：

```text
python tests/test_ui_080.py
```

PASS：

- injected JavaScript syntax (`node --check`)
- 1240px-class Desktop-first layout marker
- left list + 310px right-rail architecture
- direct single-window launcher entry
- personal/project/team space switch marker
- project/archive/sync-status/time filters
- Shift+Click range selection marker
- local archive / preflight controls
- selected / filtered / all sync actions
- pause / cancel right-rail controls
- inline result panel + copy detailed report
- obsolete report modal removal invariant
- green launcher / ChatHarbor-specific storage / half-hide scheduling

## Patcher safety

- Python syntax: PASS
- fixed upstream Git blob guard retained
- generated-runtime required marker checks retained and expanded
- build fails if obsolete preflight/integrated report modal survives final generation

## Remaining real-environment evidence

Only browser-real behavior remains to observe:

- actual responsive sizing on the user's Edge viewport;
- File System Access permission behavior;
- real launcher position persistence across reload;
- one small real sync transaction through the redesigned UI.

These are not re-opened product decisions or separate Gates.
