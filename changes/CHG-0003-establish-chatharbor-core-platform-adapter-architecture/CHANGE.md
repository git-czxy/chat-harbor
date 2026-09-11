---
id: CHG-0003
title: Establish ChatHarbor Core + Platform Adapter Architecture
type: architecture
size: S3
status: REVIEW
authority: human-owner
created: 2026-09-11
updated: '2026-09-11'
---

# CHG-0003 — Establish ChatHarbor Core + Platform Adapter Architecture

## Why

Human Decision DEC-0002 selects Extract & Recompose. Neither legacy script may remain the final product Core.

## Scope

This Change began with Architecture Specification and now contains the first minimal implementation slice plus a test-only browser integration. `ChatHarbor/` is the source module boundary; `dist/ChatHarbor-Pilot.user.js` is the self-contained installable distributable for this pilot. It does not perform large-scale business-code migration.

The first Human Browser Test found a normalization defect in ChatGPT `mapping` traversal. The correction was retested by Human and passed; this Change is now in REVIEW.

## Acceptance Review — 2026-09-11

- Core/Adapter boundary without ChatGPT-only Core assumptions: PASS — SPEC and source modules.
- Raw Source → Normalized Model → Representations fidelity/version semantics: PASS — automated tests and Human retest; unavailable contentVersion remains null.
- Attachment download versus attachment manifest separation: PASS as contract/metadata boundary; actual binary download remains outside this slice and Unknown.
- First ChatGPT slice contract, regression, and real-site evidence: PASS — Evidence file and Human Browser Retest.
- Legacy scripts preserved and not treated as final Core: PASS.
- PDR validate and commits identify the boundary: PASS.

## Dependencies

- CHG-0002 is blocked by CHG-0003.
- DEC-0001 UX decisions remain authoritative.
- DEC-0002 selects Option C.

## Stop Condition

CHG-0003 may leave READY only after its architecture specification is reviewed and implementation authorization is explicit. No Big Bang replacement is allowed.
