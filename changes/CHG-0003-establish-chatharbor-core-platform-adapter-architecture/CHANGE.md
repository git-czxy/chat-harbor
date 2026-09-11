---
id: CHG-0003
title: Establish ChatHarbor Core + Platform Adapter Architecture
type: architecture
size: S3
status: VERIFYING
authority: human-owner
created: 2026-09-11
updated: '2026-09-11'
---

# CHG-0003 — Establish ChatHarbor Core + Platform Adapter Architecture

## Why

Human Decision DEC-0002 selects Extract & Recompose. Neither legacy script may remain the final product Core.

## Scope

This Change began with Architecture Specification and now contains the first minimal implementation slice plus a test-only browser integration. `ChatHarbor/` is the source module boundary; `dist/ChatHarbor-Pilot.user.js` is the self-contained installable distributable for this pilot. It does not perform large-scale business-code migration.

## Dependencies

- CHG-0002 is blocked by CHG-0003.
- DEC-0001 UX decisions remain authoritative.
- DEC-0002 selects Option C.

## Stop Condition

CHG-0003 may leave READY only after its architecture specification is reviewed and implementation authorization is explicit. No Big Bang replacement is allowed.
