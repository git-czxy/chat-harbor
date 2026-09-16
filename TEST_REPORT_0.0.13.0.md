# ChatHarbor 0.0.13.0 — Automated Regression Report

Date: 2026-09-15

Status: **AUTOMATED REGRESSION PASS**

A real ChatGPT endpoint smoke test is still required for live rate-limit behavior and final Windows userscript generation because this build environment cannot fetch the frozen raw GitHub baseline directly.

## Existing suites retained

- planner classification matrix and LOCAL_ONLY safety;
- integrated final classification / streaming transaction order;
- repeated-verification convergence;
- Manifest-first / attachment completeness / missing-only backfill;
- Layout v1→v2 migration;
- pause/resume/cancel and wall-clock wait behavior;
- desktop UI / build invariant checks.

## New 0.0.13.0 contracts checked

```text
shared scheduler != shared speed
Discovery lane != Detail lane != Attachment metadata lane
batch pause applies only to Detail lane
global HTTP 429 cooldown is shared by all lanes
partial root/project remote snapshots are present
incomplete remote cache is displayable but not write-authoritative
cached incomplete snapshot triggers refresh again
loading UI can render discovered items instead of remaining blank
non-sync scheduler waits expose status through the loading UI
sync refuses to write from an incomplete remote universe
```

## Build contract

The PowerShell build:

1. downloads the frozen huhusmang `Tampermonkey.js` at commit `efa1f0f266d15c053af4ab4607b948a06332d9f7`;
2. verifies Git blob `3a5dfe6a696e03db7028232d45b136104e67b51f`;
3. applies the ChatHarbor patcher;
4. fails closed if lane-aware scheduler / progressive-index markers are missing or direct unscheduled backend fetches remain.

Expected output:

```text
ChatHarbor-IntegratedSync-0.0.13.0.user.js
```
