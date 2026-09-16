# ChatHarbor Clean-lineage Integrated Sync 0.0.7.0

Date: 2026-09-14

## Scope

This build continues the clean-lineage implementation on the fixed upstream:

- Repository: `huhusmang/ChatGPT-Exporter`
- Commit: `efa1f0f266d15c053af4ab4607b948a06332d9f7`
- `Tampermonkey.js` Git blob: `3a5dfe6a696e03db7028232d45b136104e67b51f`
- Upstream version: `1.5.0`

No OwlCt source is used as an implementation source. Historical ChatHarbor is used only as a behavioral/reference oracle.

## What 0.0.7.0 adds

### Conservative network policy

Default policy reimplements the historical ChatHarbor conservative behavior contract:

- speed: `较慢（推荐）` = 6000 ms base + 0–4000 ms jitter;
- detail batch size: 20 conversations;
- random inter-batch pause: 180–300 seconds;
- retry: up to 2 retries for retryable detail-fetch errors;
- 429 retry wait: conservative 120 seconds × retry attempt;
- 5xx/unknown retry wait: 30 seconds × retry attempt;
- 401/403: no blind automatic retry.

The picker contains a compact **网络策略** panel. Settings are persisted locally and are snapshotted when a new directory-sync run starts.

### Pause / resume / cancel

A running directory sync now exposes:

- `暂停`
- `继续`
- `取消同步`

Semantics:

- Pause is cooperative. An already in-flight browser request is allowed to finish, then no new detail request or new conversation transaction begins until resumed.
- Cancel is cooperative and transaction-safe. If cancellation occurs during detail verification, the remaining detail requests are not started. If it occurs while one conversation is being committed, that conversation's atomic write/manifest transaction finishes first, then the run stops before the next conversation.
- Successfully committed conversation records remain authoritative. A later sync can continue from the manifest.
- While a run is active, the picker `返回` action and background-click close are blocked. Navigation is never treated as cancellation.

## Important note about 0.0.6.1

In 0.0.6.1, clicking `返回` only closed/navigated the picker UI. It did **not** cancel the asynchronous sync task. If the tab remained open, the task could continue in the background.

Before reusing any directory touched by that run, inspect `ChatHarbor_manifest.json` and file timestamps. Per-conversation commits that completed are valid, but a test directory may contain a partial run.

## Legacy conservative archive policy

For the old dedicated conservative-export archive, the recommended migration is:

1. Keep the old archive unchanged as a read-only historical snapshot.
2. Create a **new clean canonical archive root** for clean-lineage ChatHarbor.
3. Perform one controlled initial sync into the new root after installing 0.0.7.0.
4. Verify identity count, manifest count, and selected Markdown/asset samples.
5. Only after the new archive is accepted should it become the canonical archive. Keep the legacy archive as fallback/reference until there is no longer a practical need for it.

Do **not** point the new sync engine at the legacy root merely to save the first full run. Raw JSON may be equivalent, but historical Markdown and attachment/link semantics differ. In-place adoption would create a mixed archive containing both legacy-untracked and current tracked artifacts. ChatHarbor deliberately refuses to auto-delete untracked legacy assets, so the hybrid would remain ambiguous by design.

A future one-time migration/import utility could reuse legacy raw JSON to reduce network cost, but it is not part of Core and is not required for the clean canonical archive.

## Build

Run in Windows PowerShell:

```powershell
powershell -ExecutionPolicy Bypass -File .\prepare_clean_integrated_sync.ps1
```

Output:

```text
ChatHarbor-IntegratedSync-0.0.7.0.user.js
```

The patcher verifies the fixed upstream SHA-1 Git blob before applying changes and refuses a mismatched upstream file.

## Recommended real-world acceptance

Use a **new test/canonical-candidate directory**, not the old conservative archive root.

1. Install only `ChatHarbor-IntegratedSync-0.0.7.0.user.js` and disable older experimental ChatHarbor userscripts.
2. Open the picker and confirm the conservative policy defaults.
3. Select a small set first and start directory sync.
4. During detail verification, test `暂停` → wait → `继续`.
5. Test `取消同步`; confirm no new items start afterward and already committed records remain valid.
6. Then run the full initial sync into the new archive root.

The initial 395-conversation run at the default 6–10 second pacing plus 3–5 minute pauses every 20 detail requests is intentionally slow (roughly two hours before attachment time, depending on how many detail fetches are actually required). That is expected behavior, not a stall.
