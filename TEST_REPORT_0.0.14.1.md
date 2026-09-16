# ChatHarbor 0.0.14.1 Automated Test Report

Date: 2026-09-16

## Result

**PASS — automated regression suite**

0.0.14.1 is a focused UX follow-up. It does not alter the established sync engine, request-speed presets, Archive Layout v2 transaction model, attachment backfill rules, or retry/cooldown policy.

## New 0.0.14.1 checks

### First-use guidance
- PASS: no-save-location state exposes **第一步：选择本地保存位置**.
- PASS: **选择位置** receives visual emphasis while no directory is active.
- PASS: **重新检查** is hidden until a save location exists.
- PASS: primary sync action remains disabled and explains **选择保存位置后可同步**.
- PASS: `同步选中` still cannot invoke the directory picker; only the dedicated location action can do so.

### Filter-scoped selection
- PASS: `applyFilters()` prunes selected IDs that are no longer in the current filter/search result.
- PASS: hidden conversations cannot remain silently selected after the result scope changes.
- PASS: active filters change the select-all label to **全选当前结果**.
- PASS: the sync button count is sourced from the same pruned selection set.

### Cloud-list completion feedback
- PASS: progressive loading can display the number already obtained.
- PASS: completed refresh exposes a one-shot **✓ 云端对话已加载 · 共 N 条** light-green acknowledgement.
- PASS: the completion acknowledgement auto-clears after about 1.4 seconds and is not emitted per 100-item page.

### User-facing quick-check summary
- PASS: the normal completion card uses **待同步 / 已同步 / 需确认 / 异常**.
- PASS: `NEW / UNCHANGED / LOCAL_ONLY / 待核验` do not appear in the normal quick-check completion string.
- PASS: detailed diagnostics still retain fine-grained internal state information.

## Preserved regression coverage

The following existing suites also passed:

- injected JavaScript syntax checks for all patch blocks;
- release/version/build invariants;
- scheduler lane classification;
- safer discovery/detail/attachment cadence;
- 429 adaptive slowdown and 5/10-minute cooldown;
- typed HTTP retry/error policy;
- Archive Layout v1 → v2 migration and idempotence;
- byte-identical JSON/Markdown/assets migration checks;
- untracked legacy asset preservation;
- preflight planner classification matrix;
- selective-scope LOCAL_ONLY safety;
- read-only archive scanning and duplicate/error handling;
- candidate-only detail fetching;
- streaming fetch → classify → atomic commit ordering;
- write → verify → Manifest commit → tracked-only cleanup ordering;
- Manifest-failure cleanup barrier;
- observation-checkpoint convergence;
- attachment completeness separation and missing-only backfill;
- incomplete remote-universe write stop condition;
- pause / resume / safe cancellation;
- wall-clock wait deadlines and wake guard jitter.

## Environment limitation

A real browser / ChatGPT private-backend smoke test cannot be completed in the automated container. The user-side smoke test should verify:

1. first entry with no directory clearly guides the user to **选择位置**;
2. progressive list loading shows increasing fetched counts and one completion acknowledgement;
3. filtering to **待同步 (N)** followed by **全选当前结果** produces exactly `N` selected conversations;
4. the sync button shows the same `N`;
5. the quick-check completion card contains no internal state vocabulary.

The final generated userscript is still produced locally by `prepare_clean_integrated_sync.ps1`, which downloads and verifies the pinned huhusmang baseline before applying the patch.
