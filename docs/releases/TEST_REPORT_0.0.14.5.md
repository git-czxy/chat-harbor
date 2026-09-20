# ChatHarbor 0.0.14.5 — Release Test Report

Date: 2026-09-20
Status: **AUTOMATED PASS / BROWSER SMOKE PASS / RELEASE APPROVED**

## Release artifacts

- Main userscript: `ChatHarbor.user.js`
- Historical provenance migration tool: `migration-tools/ChatHarbor-Attachment-Provenance-Backfill-0.1.1.user.js`

## Implemented scope

- attachment provenance model: `user_upload / assistant_generated_deliverable / generated_media / assistant_asset / unknown`;
- optional provenance persistence on newly processed success/failure records;
- historical failure breakdown by source, kind, stage, raw error, and source × error;
- conversation-level attachment-integrity filter and secondary gap badge;
- compact per-conversation unarchived-attachment detail view;
- inline technical drill-down;
- raw error + interpretive tooltip separation;
- one original-conversation navigation action per detail view;
- auditable `SYNC_COMPLETION` / `LOCAL_PREFLIGHT` reports;
- standalone dry-run-first provenance backfill tool with explicit Apply, backup, concurrent-Manifest guard, and non-provenance invariant verification;
- final public metadata / attribution cleanup;
- attachment detail column headers and lightweight project chips.

## Core boundary verification

PASS:

- provenance does not participate in attachment retry/sync classification;
- historical local-JSON reconstruction is not called by normal preflight/sync;
- no fifth primary user state was introduced;
- no new automatic historical attachment retry was introduced;
- unresolved account identity project-complement fix remains present;
- `LOCAL_ONLY` deletion safety and transactional write ordering remain unchanged.

## Automated validation

PASS:

- `node --check ChatHarbor.user.js`
- `node --check migration-tools/ChatHarbor-Attachment-Provenance-Backfill-0.1.1.user.js`
- `python tests/test_candidate_0145.py`
- `node tests/test_candidate_0145_runtime.js`
- `python tests/test_provenance_backfill_011.py`
- `node tests/test_conservative_policy.js`
- `node tests/test_layout_v2_migration.js`
- `node tests/test_sleep_deadline.js`
- `node tests/test_integrated_sync.js`
- `node tests/test_preflight_planner.js`

## Browser smoke — PASS

Real browser testing confirmed:

1. the four-state user model remains unchanged;
2. attachment integrity filter and `附件 N 未归档` / unarchived-attachment hints work;
3. compact attachment details render correctly;
4. field header is present and remains readable during scrolling;
5. project name is visually separated as a low-saturation chip;
6. normal-conversation `打开原会话` opens the correct conversation;
7. project-conversation `打开原会话` opens the correct conversation;
8. 403 / 404 / 415 / 500 / expired-URL explanations remain interpretive and do not claim permanent deletion/corruption;
9. final product metadata / old upstream UI wording cleanup passed.

## Provenance Dry Run — PASS

Real archive Dry Run on 2026-09-20:

- Manifest conversations: 426
- conversations with success/failure attachment evidence: 177
- local JSON read successfully: 177
- local JSON read errors: 0
- successful asset records: 749
- historical failure records: 280
- locally classified historical failures: 280
- Unknown historical failures: 0
- online complement: not required / not executed

Historical failure source summary:

- user uploads: 251
- ChatGPT-generated deliverables: 29

Raw failure summary:

- 143 × metadata HTTP 404
- 69 × download_url missing or expired
- 57 × metadata HTTP 403
- 7 × binary HTTP 415
- 4 × metadata HTTP 500

## Historical Apply status

The provenance Backfill tool's real **Apply** path was intentionally **not executed before release**. This is not a release blocker because:

- daily ChatHarbor operation does not depend on historical Apply;
- Dry Run fully reconstructs provenance for the tested archive;
- Apply is a one-time metadata enrichment path, not a content-recovery or attachment-download requirement;
- automated guards cover explicit confirmation, Manifest change detection, pre-write backup, provenance-only mutation, and read-back invariant verification.

The tool remains separate from the sync Core and defaults to Dry Run.

## Release conclusion

v0.0.14.5 is approved for public release as a local-first ChatGPT archive and integrity-audit tool.
