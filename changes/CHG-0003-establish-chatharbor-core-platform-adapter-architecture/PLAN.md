# Migration Plan — CHG-0003

## Strategy

Progressive Extract & Recompose. Do not delete either legacy script, perform a Big Bang replacement, or migrate every platform before one end-to-end slice is proven.

## Vertical slices

1. Specify and test Core contracts and compatibility mappings.
2. First slice: ChatGPT Adapter -> Common Conversation Model -> ChatHarbor Core -> confirmed Desktop-first UI -> JSON + Markdown -> attachment download plus attachment manifest -> export state/version -> batch/rate/retry/cancel.
3. Validate the complete ChatGPT slice locally and on the real site.
4. Reconnect other adapters one at a time, with adapter-specific capability evidence.

## Risk / rollback

Risk is concentrated at the Raw/Normalized boundary, version detection, attachment retrieval, and preservation of legacy state. Keep both source scripts intact as Legacy/Reference. Roll back each slice by commit; do not delete or rewrite legacy sources until equivalent evidence exists.

## Acceptance Criteria

- Core and Adapter responsibilities are documented without ChatGPT-only assumptions in Core.
- Raw Source, Normalized Model, and Representations preserve fidelity/version semantics.
- Attachment download and attachment manifest are separate capabilities.
- The first ChatGPT slice has contract, regression, and real-site evidence before other adapters migrate.
- No legacy script is deleted or assumed to be the final Core.
- PDR validate PASS and commits identify the exact architecture boundary.
