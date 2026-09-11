# CHG-0004 Implementation Evidence

- `ChatHarbor/core/versioning.js`: native-first capability-aware strategy, canonical message fingerprint fallback, explicit Unknown.
- `ChatHarbor/core/export-state.js`: four states and additive legacy ID migration.
- `ChatHarbor/export/pipeline.js`: schemaVersion, artifactVersion, sourceUpdatedAt, nullable contentVersion, representations, and attachment manifest.

Automated validation: Node syntax PASS; core vertical-slice test PASS; title-independent identity/fingerprint PASS; known equal/different versions derive `latest`/`has_updates` PASS; unknown after prior export derives `unknown` PASS; legacy exported ID migration PASS; manifest schema PASS; `git diff --check` PASS.

Not implemented or claimed: cache/incremental refresh, attachment binary download, backup/restore runtime, batch/rate/pause runtime, and UI integration.
