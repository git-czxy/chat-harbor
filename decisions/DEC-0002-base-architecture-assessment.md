---
id: DEC-0002
title: CHG-0002 Base Architecture Assessment
status: accepted
authority: human-owner
created: 2026-09-11
---

# DEC-0002 — Base Architecture Assessment

The assessment and comparison are recorded in `evidence/CHG-0002-ARCH-001-BASE-ARCHITECTURE-ASSESSMENT.md`. The following Human Decision resolves the pending recommendation without rewriting the historical assessment.

## Human Decision — 2026-09-11

Adopt Option C — Extract & Recompose. ChatHarbor will use an independent `ChatHarbor Core + Platform Adapters` architecture. Both ChatGPT v0.4 and the original generic `ai-chat-exporter` are Legacy / Reference Sources; neither is the final ChatHarbor Core.

Consequence: establish CHG-0003 before resuming CHG-0002 business implementation. DEC-0001 UX decisions remain valid.

## Human Acceptance — 2026-09-12

Human Acceptance confirms that the Option C architecture decision has been implemented and validated for the first ChatGPT vertical slice. CHG-0003 may be closed; remaining capabilities are future Changes and do not alter this decision.
