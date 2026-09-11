# Implementation / Remediation Plan — CHG-0004

Historical note: the original readiness phase is complete; this file now records the implementation/remediation phase.

## Discovery

- Confirm source fields from ChatGPT mapping, list payload, current normalized model, and legacy ID sets.
- Preserve null/Unknown where no reliable revision exists.

## Implementation sequence

1. Add version signal abstraction and canonicalization schema without changing identity.
2. Add version-aware export records alongside legacy exported/pending storage.
3. Read legacy IDs as `legacyExported: true`; do not infer latest.
4. Add state derivation and manifest/recovery compatibility tests.
5. Integrate with future pending filter only after state tests pass.

## Rollback

Keep legacy stores readable and untouched. New records are additive and schema-versioned; rollback ignores new records without deleting historical data.

## Acceptance Criteria

- No title change alters identity or content version.
- Known versions distinguish never exported, has updates, and latest.
- Unknown current version never becomes latest solely because an old export exists, and is not forced into has updates.
- One conversation supports multiple exported content versions and multiple representations per version.
- Legacy ID data is preserved and only proves prior export.
- Manifest/recovery uses identity + contentVersion, not title/filename.
- Attachment metadata and binary download remain separate.
- Specification and implementation evidence are complete; this Change remains VERIFYING pending Human Acceptance.
