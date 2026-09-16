# ChatHarbor Integrated Sync — Automated Test Report

**Date:** 2026-09-14  
**Status:** PASS — automated / static scope  
**Real browser + real File System Access acceptance:** pending one-time integration run

## Provenance checks

- Fixed upstream Git blob remains `3a5dfe6a696e03db7028232d45b136104e67b51f`.
- Integrated patcher retains hard refusal for any different upstream blob.
- Static source search: no `OwlCt` reference in the integrated patcher.
- Historical v0.4/v0.5 source was not used as an implementation source for this integrated layer.

## Parser / build checks

PASS:

- `python -m py_compile ChatHarbor_IntegratedSync_patch.py`
- extracted generated `directory_writer` + integrated sync layer parses with `node --check`
- preflight and sync handler snippets parse with `node --check`

## Preflight regression

PASS:

- NEW / VERIFY_CHANGED / VERIFY_RENAMED / UNCHANGED matrix
- selected-scope planning
- LOCAL_ONLY calculated against the full known remote universe, not the selected subset
- incomplete remote universe -> LOCAL_ONLY becomes UNKNOWN
- local duplicate IDs blocked
- remote duplicate IDs blocked at planner input
- manifest path errors blocked
- `*_files` asset directories are skipped during conversation JSON discovery
- non-conversation JSON does not become a false conversation

## Real Gate-3.1 Manifest compatibility smoke

Using the actual provided Gate-3.1 manifest fixture:

- local identities: 2
- manifest tracked: 2
- duplicate IDs: 0
- scan errors: 0
- equivalent remote fixture -> UNCHANGED: 2
- maximum detail fetch required: 0

No manifest schema migration is required.

## Final-classification regression

PASS:

- NEW
- UPDATED
- RENAMED_ONLY
- UPDATED_AND_RENAMED
- METADATA_ONLY by timestamp/metadata change with equal content signature
- UNCHANGED with equal signature/title/metadata/time
- LOCAL_UNTRACKED is kept distinct rather than falsely asserting a content change
- missing authoritative local signature -> ERROR

## Detail-fetch minimization

PASS:

Only preflight items marked `needs_detail_fetch` are fetched.

- UNCHANGED: no detail fetch
- DUPLICATE: no detail fetch
- ERROR: no detail fetch
- NEW / verify candidates: detail fetch

## Transaction safety

PASS:

- normal rename/update ordering: `write -> manifest -> cleanup`
- manifest failure prevents cleanup
- in-place METADATA_ONLY performs manifest-only commit
- project/path relocation recalculates Markdown attachment links relative to the new Markdown location
- cleanup only removes old manifest-tracked paths
- asset directory cleanup is non-recursive
- untracked legacy assets survive cleanup
- full sync stops before disk scan/write if the remote universe is incomplete

## Remaining evidence boundary

Automated tests cannot replace the current browser session, ChatGPT backend responses, or the browser File System Access implementation. Therefore the only remaining acceptance is one integrated real-environment run on a copy of the real archive. No intermediate Human Acceptance gates are required.
