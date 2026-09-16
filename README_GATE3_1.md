# ChatHarbor Clean-lineage — Gate 3.1

Gate 3 core has passed in real use. This patch fixes two concrete issues found during acceptance.

## Fix 1 — completion is non-blocking

The previous synchronous browser `alert()` could appear while the last painted frame still showed 96%.

The operation was already complete, but the modal blocked rendering.

Gate 3.1 removes that completion alert.

Expected result:
- progress panel reaches **100% immediately**;
- floating launcher reaches the completion state immediately;
- no “确定” click is required to finish or reveal 100%.

## Fix 2 — unchecking attachments does not erase tracked attachment state

If a conversation already has a tracked `asset_dir` / `assets` record and a later write is run with “同时下载上传和生成的附件” unchecked:

- existing files are **not deleted**;
- existing `asset_dir` is preserved;
- existing `assets` entries are preserved;
- existing attachment counts/failures are preserved;
- manifest records `attachments_preserved_without_download: true`.

This gives the checkbox the intended meaning:

> Do not download/refresh attachments this run.

It does **not** mean:

> Forget or delete attachments that are already part of the local archive.

Newly downloaded asset records also store:
- `source_file_id`
- `source_sandbox_path`

so later Markdown can reuse existing local resource links without redownloading.

For the one-time transition from a Gate-3 manifest that lacks original sandbox paths, Gate 3.1 preserves the existing Markdown rather than degrading working local links.

## Acceptance A — 100% visibility

Write one conversation.

PASS when:
- no blocking completion alert appears;
- picker remains open;
- progress visibly reaches 100%;
- floating ball shows completion.

## Acceptance B — reverse attachment test

Use the same conversation that already has 10 tracked attachments.

1. Confirm manifest shows 10 assets.
2. Uncheck attachment download.
3. Write the same conversation again.

PASS when:
- manifest conversation count does not change;
- same `conversation_id` key is updated;
- `asset_dir` remains the same;
- `assets` remains 10;
- physical `_files` directory remains untouched;
- `attachments_preserved_without_download` is `true`.

## Acceptance C — normal attachment refresh

Check attachment download and write the same conversation again.

PASS when:
- attachments are downloaded normally;
- asset metadata is refreshed;
- new records contain `source_file_id` / `source_sandbox_path` when available;
- `attachments_preserved_without_download` is `false`.

After A+B pass, Gate 3.1 can be frozen and development can move to:

**Local Archive Scan + Version-aware Classification.**
