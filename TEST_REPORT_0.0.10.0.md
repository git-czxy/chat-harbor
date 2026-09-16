# ChatHarbor 0.0.10.0 — Automated Regression Report

Date: 2026-09-14

## Result

**PASS — automated regression. Real Windows/Edge File System Access migration smoke remains the only environment-specific acceptance step.**

## Archive Layout v2 / migration

- PASS — Layout v1 → v2 migration is local-only; the migration path never calls conversation-detail or attachment-fetch functions.
- PASS — non-project target path is `conversations/...`.
- PASS — project target path is `projects/<project>/...`.
- PASS — copied JSON, Markdown and tracked asset bytes are SHA-256 verified before Manifest authority moves to the new path.
- PASS — per-conversation migration is resumable after new Manifest path commit but before old-path cleanup.
- PASS — untracked legacy asset material is preserved; old asset directories are not recursively deleted.
- PASS — rerunning migration against an already-v2 archive is a no-op.
- PASS — migrated conversations remain eligible for fast-path `UNCHANGED` when remote metadata is unchanged; layout movement alone does not require detail fetch.
- PASS — normal sync is blocked while Layout v1 / incomplete layout migration is detected.

## Real Manifest structural preflight

A structural target-mapping check was run against the user-provided current Manifest without copying any private archive content into this package:

- tracked conversations: 83
- project conversations: 58
- non-project conversations: 25
- JSON + Markdown target files: 166
- tracked asset directories: 31
- tracked asset files: 214
- Layout v2 target-path collisions: **0**

This is a path-mapping check only; the browser migration still performs actual source existence and byte/hash verification on the user's disk.

## Existing regression suite

- PASS — Planner classification matrix.
- PASS — selective-scope `LOCAL_ONLY` protection.
- PASS — duplicate/error/`_files` scanner handling.
- PASS — canonical remote-universe merge.
- PASS — final NEW / UPDATED / RENAMED_ONLY / UPDATED_AND_RENAMED / METADATA_ONLY / UNCHANGED classification.
- PASS — write → Manifest commit → tracked-only cleanup ordering.
- PASS — Manifest failure prevents cleanup.
- PASS — in-place METADATA_ONLY remains Manifest-only.
- PASS — streaming fetch → classify → atomic commit ordering.
- PASS — conservative defaults 6–10s / 20 detail requests / 180–300s batch pause.
- PASS — pause / resume / safe cancellation.
- PASS — wall-clock sleep deadline, wake guard, live MM:SS batch countdown.
- PASS — cached canonical account index and local all/project switching.
- PASS — single selection sync scope and tri-state select-all.
- PASS — project known / none / unknown distinction.
- PASS — automatic local scan + manual rescan.
- PASS — `当前第 X / N 条` runtime wording and distinct archived amber pill.
- PASS — injected JavaScript blocks pass `node --check`.
- PASS — Python patcher passes syntax compilation.

## Clean-lineage guard

- Fixed upstream remains `huhusmang/ChatGPT-Exporter` commit `efa1f0f266d15c053af4ab4607b948a06332d9f7`.
- Expected `Tampermonkey.js` Git blob remains `3a5dfe6a696e03db7028232d45b136104e67b51f`.
- Patcher still refuses a different upstream blob.
- No OwlCt implementation was introduced.

## Deferred intentionally

Source normalization / module split, test/runtime code deduplication, and removal of inherited ZIP/legacy runtime paths are **not** mixed into 0.0.10.0. They remain the next pre-1.0 refactor after real Layout v2 migration smoke testing, so archive-format change and code-structure change are not coupled in one acceptance step.
