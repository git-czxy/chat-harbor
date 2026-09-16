# ChatHarbor Clean-lineage — Gate 3

## Entry condition

Confirmed before this gate:

- Gate 2A ordinary conversation directory write: **PASS**
- Gate 2B isolated attachment directory: **PASS**
- Gate 2C Markdown local asset links: **PASS (user confirmed)**

Clean upstream remains fixed at:

- `huhusmang/ChatGPT-Exporter`
- commit `efa1f0f266d15c053af4ab4607b948a06332d9f7`
- `Tampermonkey.js` git blob `3a5dfe6a696e03db7028232d45b136104e67b51f`

## Gate 3 adds

1. `conversation_id` is the canonical archive identity.
2. Root-level `ChatHarbor_manifest.json`.
3. One manifest record per conversation, keyed by `conversation_id`.
4. Manifest is committed **after** JSON / Markdown / selected assets have been written and verified.
5. SHA-256 content signature is recorded over `current_node + mapping`.
   - It is recorded only.
   - Gate 3 does **not** yet use it to classify UPDATED/UNCHANGED.
6. Per-conversation isolated asset directory is recorded in the manifest.
7. Visible progress feedback is added to the existing picker so long attachment runs are not silent.

## Manifest record

A successful conversation commit records at least:

- `conversation_id`
- title
- create/update time
- archive/project metadata
- content signature + signature version
- JSON path + byte size
- Markdown path + byte size
- isolated `asset_dir`
- asset paths + sizes
- attachment success/failure counts
- `synced_at`

## Safety rules

- Existing invalid/corrupt manifest is **not silently overwritten**.
- `conversation_id` missing => refuse manifest commit.
- Files are written before the manifest record is committed.
- A manifest write failure means the conversation is reported failed even if some files already exist.
- No automatic deletion is performed.
- No rename cleanup is performed.
- No remote/local version classification is performed yet.

## Run

```powershell
powershell -ExecutionPolicy Bypass -File .\prepare_clean_gate3.ps1
```

Install the generated `ChatHarbor-Gate3.user.js`.

Use a **test/copy directory**, not the sole canonical archive.

## Acceptance test A — first identity commit

1. Select one known conversation.
2. Click `写入选中到目录 (1)`.
3. Confirm progress is visible during:
   - conversation fetch;
   - attachment download if enabled;
   - JSON write;
   - Markdown write;
   - signature;
   - manifest commit.
4. Verify root contains `ChatHarbor_manifest.json`.
5. Verify `manifest.conversations` contains a key exactly equal to that conversation's full `conversation_id`.
6. Verify paths in that record exist.

Expected: manifest count = 1 in a new empty test directory.

## Acceptance test B — idempotent identity key

Run the **same conversation again** into the same directory.

Expected:

- `manifest.conversations` still contains only one record for that `conversation_id`;
- no second manifest identity is created;
- `synced_at` is refreshed;
- JSON/Markdown are rewritten in place using the same current title-derived paths.

This tests **identity idempotence only**. It is not yet a Version-aware no-op test.

## Acceptance test C — second conversation

Write a different conversation.

Expected:

- manifest count becomes 2;
- each record has a distinct `conversation_id`;
- each attachment-bearing conversation retains its own `_files` directory.

## Stop condition

Gate 3 passes when:

- manifest schema is readable;
- full `conversation_id` is authoritative;
- repeat write updates the same manifest key;
- asset directory/path records are correct;
- visible progress eliminates the long silent period;
- no unintended deletion or ZIP is triggered by the directory-write action.

Only then proceed to local archive scan + Version-aware classification.
