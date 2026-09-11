# CHG-0004 Implementation Evidence

- `ChatHarbor/core/versioning.js`: native-first capability-aware strategy, canonical message fingerprint fallback, explicit Unknown.
- `ChatHarbor/core/export-state.js`: four states and additive legacy ID migration.
- `ChatHarbor/export/pipeline.js`: schemaVersion, artifactVersion, sourceUpdatedAt, nullable contentVersion, representations, and attachment manifest.

Automated validation: Node syntax PASS; core vertical-slice test PASS; title-independent identity/fingerprint PASS; known equal/different versions derive `latest`/`has_updates` PASS; unknown after prior export derives `unknown` PASS; legacy exported ID migration PASS; native revision precedence PASS; same-version representation/artifact-reference merge PASS; manifest required fields and identity+version recovery match PASS; derived fingerprint enters artifact JSON and manifest PASS; `git diff --check` PASS.

Not implemented or claimed: cache/incremental refresh, attachment binary download, backup/restore runtime, batch/rate/pause runtime, and UI integration.

## Review remediation round 2

Regression tests cover legacy exported→observe-known→unknown, pending coexistence, null-version recovery, distinct unknown artifact IDs, content/title fingerprint behavior, native precedence, no-signal Unknown, derived version propagation into JSON/manifest, required manifest fields, and identity+version recovery matching. The manifest claim is limited to the tested schema and recovery core; it does not claim full ZIP/backup runtime.

## Review remediation round 3

Known observed versions now remain `unknown` when any prior successful artifact has an incomparable null version and no equal known version exists; `has_updates` requires all prior successful versions to be comparable and different. Legacy pending remains a retry/processing hint. Unknown artifacts merge and recover only by persisted `artifactId`; known artifacts recover by identity plus contentVersion without requiring artifactId. Tests cover artifact isolation and same-instance representation merge.
