---
id: CHG-0004
title: Establish Version-aware Export State
type: refactor
size: S2
status: VERIFYING
authority: human-owner
created: 2026-09-12
updated: '2026-09-12'
---

# CHG-0004 — Establish Version-aware Export State

## Why

建立 ChatHarbor 的版本感知导出状态，使同一 Conversation 的多次导出可恢复、可比较，并避免标题变化被误判为内容更新。

## Current Behavior

Confirmed: identity is `platform + conversationId`; title is display-only; current ChatGPT `contentVersion` is allowed to be null. Legacy stores exported/pending ID sets only. Reliable ChatGPT content revision is not yet confirmed.

## Desired Behavior

为 Core 定义并实现可迁移的 Content Version、Export State、Manifest 和恢复语义；仍未接入 UI、cache、附件下载或 batch runtime。

## Scope

### In

- Version-aware content observation and export state implementation.
- Legacy exported/pending additive migration.
- Versioned artifact manifest and identity/version recovery compatibility core.

### Out

- Production UI integration.
- Cache/incremental refresh.
- Attachment binary download.
- Full ZIP/backup runtime.
- Batch/rate/pause runtime.

## Acceptance Criteria

- [x] Capability-aware hybrid strategy with native precedence and deterministic fingerprint fallback.
- [x] Four-state export model preserves Unknown and does not use title/version timestamps as content version.
- [x] Legacy exported/pending data migrates additively without claiming Latest.
- [x] Successful export records observed contentVersion in artifact and manifest.
- [x] Same-version representations and artifact references merge without loss.
- [x] Manifest/recovery core matches stable identity + contentVersion.
- [x] Automated tests cover state transitions, migration, fingerprint, native precedence, pipeline, manifest, and recovery.

## Decisions

- DEC-0001 UX identity/version decisions remain authoritative.
- This implementation/remediation pass is technical contract work; it does not create or alter a Human Product Decision.
- Human Acceptance is the only remaining Human Gate before closure.

## Unknowns

- ChatGPT native reliable content revision remains unavailable; derived fingerprint is used only when normalized content exists, otherwise Unknown.
- Full ZIP/backup runtime, cache/incremental refresh, attachment binary download, and production UI remain outside this Change.

## Stop Condition

This change is ready to close when all Acceptance Criteria have Evidence and required Human Acceptance is recorded.
