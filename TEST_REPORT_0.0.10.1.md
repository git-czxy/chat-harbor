# ChatHarbor 0.0.10.1 — Automated Regression Report

Status: **PASS — automated regression**

Real-browser smoke still required for final visual confirmation of the fixed-left selection bar and disabled settings styling.

## UI / state-consistency checks

- PASS provider-only header marker; duplicate scope/archive context removed from header
- PASS Local archive explicit `目录：<name>` label
- PASS `归档详情` wording
- PASS selection status anchored left with fixed spacing after `全选`
- PASS `已选 / 当前 / 共` semantics use canonical provider universe for total
- PASS collapsed `同步内容 · 下载附件 / 不下载附件` summary
- PASS network and sync-content lock notes exist
- PASS active run disables network controls and attachment checkbox
- PASS active run disables search/filter/scope and individual conversation selection
- PASS sync start captures an explicit attachment/network run snapshot
- PASS integrated sync receives the run snapshot rather than mutable UI state
- PASS guarded change handlers cannot mutate effective run settings

## Preserved regression checks

- PASS Layout v1 → v2 local-only migration
- PASS v2 `conversations/` + `projects/<project>/` namespace paths
- PASS byte-identical JSON / Markdown / tracked assets after migration
- PASS untracked legacy preservation and resumable migration
- PASS migrated unchanged conversations return to fast-path `UNCHANGED`
- PASS Planner classification matrix and LOCAL_ONLY safety
- PASS candidate-only detail fetch
- PASS streaming Fetch → Classify → Atomic Commit → Manifest
- PASS write → verify → Manifest commit → tracked-only cleanup ordering
- PASS conservative defaults 6–10s / batch 20 / 180–300s
- PASS retry, pause/resume, safe cancel
- PASS absolute wall-clock deadlines, wake guard and MM:SS batch countdown
- PASS injected JavaScript syntax for all ChatHarbor blocks

## Core scope

No Archive Layout, Manifest schema, content-signature, remote classification or network-timing algorithm was changed in 0.0.10.1. This release changes UI information hierarchy and enforces consistency between displayed settings and the already-running task.
