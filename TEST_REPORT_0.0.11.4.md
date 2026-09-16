# ChatHarbor 0.0.11.4 Test Report

Automated regression suite: PASS.

## New 0.0.11.4 assertions

- PASS legacy positive attachment evidence infers `complete` without a redundant detail candidate.
- PASS legacy partial/failed evidence remains `partial` and retryable.
- PASS ambiguous legacy zero-count attachment evidence remains `unknown`.
- PASS a 3-reference backfill with 2 matching Manifest assets fetches only the 1 missing reference.
- PASS reused asset paths remain root-relative Manifest paths and Markdown links are recalculated for the current conversation location.
- PASS attachment progress for that backfill is monotonic (`2/3`, then `3/3`) and no pre-download duplicate counter is emitted.
- PASS build-time runtime markers fail closed if legacy inference, missing-only planning, or monotonic progress code disappears.
- PASS generated userscript metadata source is explicitly `@version 0.0.11.4`.

## Inherited regression coverage

- repeated-verification convergence via `remote_list_*` observation checkpoints;
- Manifest-first local index;
- persistent Remote Index cache + 20-item fast-head validation + periodic full refresh;
- candidate-only detail fetch and actionable-only runtime denominator;
- write -> Manifest commit -> tracked-only cleanup transaction ordering;
- attachment/content state separation;
- Layout v1 -> v2 resumable local-only migration;
- conservative request pacing, retries, pause/resume, safe cancel;
- absolute wall-clock wait / sleep-wake reconciliation;
- desktop workspace UI and run-state locking.

Core injected-layer SHA-256:

```text
bbedde8bf63d1e8c0e93b742db71d5b3b6012f8763174338be7baab4ad34ff78
```
