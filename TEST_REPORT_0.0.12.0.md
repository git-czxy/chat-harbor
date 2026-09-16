# ChatHarbor 0.0.12.0 — Automated Regression Report

Date: 2026-09-15

Status: **AUTOMATED REGRESSION PASS**

A real ChatGPT endpoint smoke test is still required for live rate-limit behavior and final userscript generation on Windows, because this build environment cannot download the frozen raw GitHub baseline directly.

## Passed suites

- `test_preflight_planner.js`
  - planner classification matrix
  - selective-scope LOCAL_ONLY safety
  - read-only archive duplicate/error handling
- `test_integrated_sync.js`
  - final classification matrix
  - remote-universe merge / ambiguity preservation
  - remote-head fingerprint change detection
  - attachment link relocation
  - candidate-only detail fetch
  - write -> Manifest -> cleanup ordering
  - Manifest-failure cleanup barrier
  - METADATA_ONLY / OBSERVATION_ONLY Manifest-only commit
  - repeated-verification convergence checkpoint
  - attachment completeness separation
  - tracked-only cleanup safety
  - incomplete-universe stop condition
  - streaming fetch -> classify -> commit order
  - Preflight-confirmed fast skip from runtime denominator
- `test_conservative_policy.js`
  - conservative defaults
  - retry-delay classification
  - pause/resume
  - graceful cancellation
  - runtime navigation guards
- `test_sleep_deadline.js`
  - live countdown formatter
  - absolute wall-clock wait semantics
  - sleep/wake guard
- `test_layout_v2_migration.js`
  - local-only Layout v1 -> v2 migration
  - byte-identical migration
  - untracked asset preservation
  - resumability/idempotence
  - post-migration UNCHANGED fast path
- `test_ui_0120.py`
  - injected JavaScript syntax for main runtime/UI blocks
  - desktop UI invariants
  - cached Remote Index markers
  - convergent Manifest checkpoint markers
  - attachment incremental markers
  - shared backend scheduler / global cooldown markers
  - remote refresh single-flight / snapshot freeze markers
  - physical attachment integrity / Manifest rollback markers
  - commit-accurate visible-state markers
- `test_release_0120.py`
  - version/build naming
  - fail-closed release markers
  - cross-cutting 0.0.12.0 runtime invariants

## New 0.0.12.0 correctness contracts checked

```text
all ChatHarbor /backend-api control requests -> one scheduler
HTTP 429 -> one global cooldown
signed/direct binary transfer -> separate transfer path; 429 still advances global cooldown
background remote refresh -> single-flight; cannot mutate active-run snapshot
classified != committed
Manifest asset identity != physical asset existence
Manifest commit failure -> newly written attachment cleanup + in-memory record rollback
```

## Build contract

The PowerShell build still:

1. downloads the frozen huhusmang `Tampermonkey.js` at commit `efa1f0f266d15c053af4ab4607b948a06332d9f7`;
2. verifies Git blob `3a5dfe6a696e03db7028232d45b136104e67b51f`;
3. applies the ChatHarbor patcher;
4. fails closed if required runtime markers are missing or direct unscheduled backend fetch markers remain.

Expected output:

```text
ChatHarbor-IntegratedSync-0.0.12.0.user.js
```
