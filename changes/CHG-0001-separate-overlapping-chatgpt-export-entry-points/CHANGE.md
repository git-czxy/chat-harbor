---
id: CHG-0001
title: Separate overlapping ChatGPT export entry points
type: bug
size: S1
status: REVIEW
authority: human-owner
created: 2026-09-11
updated: '2026-09-11'
---

# CHG-0001 — Separate overlapping ChatGPT export entry points

## Why

When both the ChatGPT-specific exporter and the generic `ai-chat-exporter` Userscript are enabled on a ChatGPT page, their floating entry buttons occupy the same bottom-right area and can overlap.

## Current Behavior

Confirmed from the current scripts: the generic script creates one `button` in `mountButton()` and appends it to `document.body` with `position: fixed`, `right: 20px`, `bottom: 20px`, `zIndex: 99999`. The ChatGPT v0.4 script creates one button in `addBtn()` and appends it to `document.body` with `position: fixed`, `right: 24px`, `bottom: 24px`, `zIndex: 99997`. Their independent fixed anchors are therefore in the same visual region. Actual browser reproduction remains Unknown in this offline environment.

## Desired Behavior

Keep both existing entry buttons visible and independently clickable while separating their default positions with a small, stable vertical offset. Preserve each script's existing click handlers and export flow.

## Scope

### In

- Adjust only the generic script's floating button position.
- Record static evidence and the remaining real-site Unknown.

### Out

- No UI redesign or shared container.
- No changes to dialogs, export logic, labels, z-index policy, or the ChatGPT-specific button.
- No UX-001 work or provenance/license work.

## Acceptance Criteria

- [x] Both entry buttons remain present in the two current script code paths.
- [x] Both entry buttons retain independent click handlers in the current code.
- [ ] Default desktop positioning is confirmed non-overlapping in a real ChatGPT page.
- [x] No new duplicate DOM entry is introduced by the one-property change.
- [x] Existing export code paths are unchanged by this positioning-only fix.
- [x] Offline-verifiable static checks pass; real ChatGPT behavior remains Unknown unless tested in the site.

## Decisions

- Use a vertical offset on the generic button (`bottom: 80px`) while retaining its right alignment. This is the smallest fix because the two scripts already own separate buttons and click handlers.

## Unknowns

- Exact rendered button dimensions and overlap behavior on a real ChatGPT page cannot be measured offline.
- Real-site click and export regression behavior is not available in this environment.

## Stop Condition

This change is ready to close when all Acceptance Criteria have Evidence and required Human Acceptance is recorded.
