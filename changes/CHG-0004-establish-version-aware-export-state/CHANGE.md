---
id: CHG-0004
title: "Establish Version-aware Export State"
type: refactor
size: S2
status: READY
authority: human-owner
created: 2026-09-12
---

# CHG-0004 — Establish Version-aware Export State

## Why

建立 ChatHarbor 的版本感知导出状态，使同一 Conversation 的多次导出可恢复、可比较，并避免标题变化被误判为内容更新。

## Current Behavior

Confirmed: identity is `platform + conversationId`; title is display-only; current ChatGPT `contentVersion` is allowed to be null. Legacy stores exported/pending ID sets only. Reliable ChatGPT content revision is not yet confirmed.

## Desired Behavior

为 Core 定义可实现、保守且可迁移的 Content Version、Export State、Manifest 和恢复语义。本轮只完成 Discovery、Specification、Implementation Readiness。

## Scope

### In

- Content version candidate analysis and state model specification.
- Legacy exported/pending migration rules.
- Manifest/recovery schema and acceptance evidence plan.

### Out

- Business-code implementation.
- Cache/incremental refresh implementation.
- Attachments download, batch/rate/pause, backup/restore implementation.

## Acceptance Criteria

- [x] Discovery records source-confirmed signals and Unknowns.
- [x] Specification defines version candidates, state transitions, unknown semantics, manifest, and migration.
- [x] Implementation readiness is recorded without business-code changes.

## Decisions

- DEC-0001 UX identity/version decisions remain authoritative.
- No new Human Product Decision is required for readiness; unknown-version semantics are specified conservatively for implementation review.

## Unknowns

- Implementation may begin only after this READY Change is explicitly authorized.

## Stop Condition

This change is ready to close when all Acceptance Criteria have Evidence and required Human Acceptance is recorded.
