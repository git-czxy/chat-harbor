# ChatHarbor Gate 4A — Test Report

Status: **automated tests PASS; real browser/local-archive dry-run still required before Gate 4A acceptance**.

## Automated classification matrix

PASS:

- manifest-tracked same title + same remote update time -> `UNCHANGED`;
- title-only difference -> `VERIFY_RENAMED`;
- update-time difference/unknown -> `VERIFY_CHANGED`;
- title + update-time difference -> one fetch candidate, not double-counted;
- raw-only local conversation -> verification candidate, not assumed synced;
- missing local identity -> `NEW`;
- local duplicate ID -> `DUPLICATE`, no detail fetch;
- duplicate remote ID visible to planner -> `DUPLICATE`, no detail fetch;
- metadata-only prefilter difference -> verification candidate;
- raw-only local identities require verification without being falsely counted as remote-update candidates when timestamps match;
- selective scope changes candidate counts but does not redefine the remote universe used by `LOCAL_ONLY`;
- incomplete remote-universe coverage -> `LOCAL_ONLY` becomes `UNKNOWN`, not a false positive.

Synthetic matrix result:

```text
Remote: 9 entries / 8 unique IDs
Local: 7 IDs
NEW: 1
remote-update candidates: 2
rename candidates: 2
UNCHANGED: 1
metadata candidates: 0
raw-only verify candidates: 1
LOCAL_ONLY: 1
duplicate IDs: 2
ERROR: 0
maximum fetch required: 5
```

## Read-only archive scanner

PASS:

- readable Gate-3 manifest accepted only with expected `schema_version`, `identity=conversation_id`, and signature version;
- manifest `json_path` missing on disk is reported as `ERROR` and blocks that ID;
- two raw conversation JSON files with one `conversation_id` are reported as `DUPLICATE`;
- arbitrary/broken JSON outside asset directories is ignored rather than fabricated as archive corruption;
- directories ending `_files` are skipped for conversation parsing, so JSON attachments cannot become false conversation identities;
- no scanner code path writes, deletes, renames, commits manifest, or fetches remote conversation details.

## Real Gate-3.1 manifest compatibility smoke

The actual two-record Gate-3.1 manifest supplied from the validated run was loaded against a synthetic file-handle shell matching its tracked JSON paths.

PASS:

```text
Local identities: 2
Manifest tracked: 2
Duplicate IDs: 0
Manifest/path errors: 0
Asset directories skipped for conversation parsing: 1
Equal remote-list fixture -> UNCHANGED: 2
maximum fetch required: 0
```

This confirms schema/interface compatibility only. It is **not** a substitute for the required browser dry-run against the user's real local archive and current authenticated ChatGPT remote lists.

## Gate 4A stop condition

Do not mark Gate 4A PASS/FROZEN until one real browser dry-run demonstrates:

1. real remote universe completion succeeds;
2. real archive scan completes read-only;
3. summary reports Remote / Local / NEW / remote-update candidates / rename candidates / UNCHANGED / LOCAL_ONLY / duplicate IDs / maximum fetch required;
4. no conversation detail requests are made by the preflight action;
5. `ChatHarbor_manifest.json` and archive file timestamps/content remain unchanged by the preflight action;
6. results are plausible enough to proceed to detail-fetch verification.
