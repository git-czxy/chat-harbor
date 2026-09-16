# ChatHarbor Clean-lineage — Integrated Version-aware Selective Sync

## Status

**READY FOR ONE-TIME REAL-ENVIRONMENT ACCEPTANCE**

This is the integrated delivery for the current conversation scope:

- Local Archive Scan
- Version-aware Classification
- Selective Sync

It does **not** require separate Human Acceptance between internal implementation steps.

## Fixed lineage

- Direct upstream: `huhusmang/ChatGPT-Exporter`
- Commit: `efa1f0f266d15c053af4ab4607b948a06332d9f7`
- `Tampermonkey.js` Git blob: `3a5dfe6a696e03db7028232d45b136104e67b51f`
- Upstream version: `1.5.0`
- License: MIT

The patcher refuses a different upstream blob.

Historical ChatHarbor v0.4/v0.5 remains behavioral/reference evidence only. No OwlCt source is imported into this clean-lineage patch.

## What the integrated build does

The directory path is now:

```text
Remote list
  -> Local Archive Scan
  -> Preflight Planner
  -> fetch only NEW / verify candidates
  -> content_signature verification
  -> final classification
  -> Selective / Full Directory Sync
  -> per-conversation manifest commit
  -> tracked-only post-commit cleanup
```

Final states include:

- `NEW`
- `UNCHANGED`
- `UPDATED`
- `RENAMED_ONLY`
- `UPDATED_AND_RENAMED`
- `METADATA_ONLY`
- `LOCAL_ONLY`
- `DUPLICATE`
- `ERROR`

An additional conservative diagnostic state is used for raw local conversations that are not manifest-authoritative:

- `LOCAL_UNTRACKED`

It is synchronized into the canonical archive without deleting the old untracked source path/assets.

## Safety invariants

1. `conversation_id` is the identity. Title is never identity.
2. `update_time` is only a prefilter. Final content truth uses `sha256-current_node+mapping-v1`.
3. Title difference is checked independently of `update_time`.
4. `LOCAL_ONLY` is never automatically deleted.
5. Duplicate IDs are blocked and reported, not auto-resolved.
6. A full sync is refused if the remote universe cannot be completed.
7. Selected sync can still operate on explicitly selected remote IDs without pretending LOCAL_ONLY is known.
8. Rename/update ordering is:

```text
write new files
-> verify writes
-> manifest commit
-> cleanup old tracked paths
```

9. If manifest commit fails, cleanup does not run.
10. Cleanup only removes exact paths that were tracked by the previous manifest.
11. Asset directories are never recursively deleted. Old tracked asset files may be removed after commit; any untracked legacy file causes the directory to remain.
12. If attachment download is disabled, prior tracked attachment state is preserved. When Markdown moves across project directories, local attachment links are recalculated relative to the new Markdown location.
13. `METADATA_ONLY` uses a manifest-only commit when storage paths do not need relocation.

## UI behavior

The existing huhusmang conversation picker remains the only selector.

- Select one or more conversations -> `目录同步（选中 N）`
- Select none -> `目录同步（全部 N）`
- `目录预检` remains a read-only dry-run action.
- Upstream ZIP export remains a separate compatibility path in this build and is not used as sync authority.

## Build on Windows

Unzip the package and run:

```powershell
powershell -ExecutionPolicy Bypass -File .\prepare_clean_integrated_sync.ps1
```

This downloads the exact fixed upstream file and generates:

```text
ChatHarbor-IntegratedSync.user.js
```

Install that userscript in Tampermonkey.

## One-time real-environment acceptance

Use a **copy of the real ChatHarbor archive**, not the only canonical copy, for this acceptance run.

Before running sync:

```powershell
Get-FileHash .\ChatHarbor_manifest.json -Algorithm SHA256
```

Then perform one integrated session:

1. Open the existing picker and wait for the remote list to finish loading.
2. Run `目录预检（全部 N）` against the copied archive.
3. Confirm the report contains Remote / Local / NEW / candidates / UNCHANGED / LOCAL_ONLY / duplicates / ERROR / maximum fetch required.
4. Without creating a second selector, leave all checkboxes clear and run `目录同步（全部 N）`.
5. Review the final integrated report.
6. Re-open the copied archive and confirm:
   - `ChatHarbor_manifest.json` parses;
   - keys remain full `conversation_id` values;
   - unchanged conversations were not detail-fetched;
   - changed candidates reached final signature-based classifications;
   - LOCAL_ONLY content still exists;
   - duplicate/error identities were not rewritten;
   - renamed paths only lost their old tracked JSON/Markdown after the new record was committed;
   - untracked files inside legacy asset directories remain present;
   - attachment state is preserved when attachment download is unchecked.

If the remote universe cannot be completed, full sync must stop before writes. This is a PASS condition for the safety barrier, not a reason to weaken it.

## Stop condition for this stage

This stage is accepted once the single real-environment integration run confirms:

- browser/API integration works against the current ChatGPT session;
- File System Access behavior matches the automated transaction model;
- no safety invariant above is violated.

Do not reopen Exporter fidelity, Directory Writer, or Manifest design unless the integrated run produces contradictory evidence.

## Deferred, not blockers for this stage

The following remain later clean-lineage work:

- port the historical multi-level conservative network policy (speed levels / batch limit / long random pause / retry / cancel);
- finish explicit `zh-CN` + `en-US` resources;
- remove or relocate upstream ZIP compatibility code after directory sync is accepted;
- optional local-archive snapshot ZIP, if ever retained.
