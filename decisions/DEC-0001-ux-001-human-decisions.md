---
id: DEC-0001
status: active
authority: human
created: 2026-09-11
supersedes: null
---

# DEC-0001

## Decision

Adopt the UX-001 Human Decisions supplied in the task: Desktop-first single workspace; compact toolbar; adapter-provided scope; distinct archive/export filters; stable identity plus versioned artifact semantics; logical-list selection; compact time control; cached/incremental refresh; right-side control rail; persistent export strategy; concise confirmation; and explicit progress/cancellation/retry behavior.

## Context

These decisions are the product authority for CHG-0002 and are not inferred from the historical Trae plan.

## Consequences

The implementation must preserve platform-specific adapter capability boundaries, must not use titles for identity, and must keep Unknown version signals explicit.

## Rejected Alternatives

Do not reopen the supplied decisions during this Discovery/Specification pass.

## Affects

- CHG-0002 UX specification and future implementation Changes.

## Evidence / Source

Explicit Human Decision in the UX-001 task message, 2026-09-11.

## Update — 2026-09-11

The Human Owner further decided that ChatGPT v0.4 will be discontinued as a product tool. ChatHarbor is the sole future primary product; v0.4 remains unchanged as Legacy / Reference Implementation for capability and interaction comparison. New capability work goes into the ChatHarbor generic architecture. Migration of the new workspace back into v0.4 is superseded and must not be pursued. This update does not rewrite the historical v0.4 source.
