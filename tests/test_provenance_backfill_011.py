import pathlib, re, subprocess
ROOT=pathlib.Path(__file__).resolve().parents[1]
artifact=ROOT/'migration-tools'/'ChatHarbor-Attachment-Provenance-Backfill-0.1.1.user.js'
assert artifact.exists(), artifact
text=artifact.read_text(encoding='utf-8')
subprocess.run(['node','--check',str(artifact)],check=True,capture_output=True,text=True)
assert re.search(r'^// @version\s+0\.1\.1\s*$',text,re.M)
for marker in [
    'runLocalAudit','applyProvenanceBackfill','应用来源补全','pre_attachment_provenance_backfill_',
    'stripProvenanceForInvariant','owner_role','source_category','reference_kind',
    'Manifest 在 Dry Run 后已经发生变化','备份 Manifest 校验失败','写回验证失败'
]: assert marker in text, marker
# Dry run remains default; writes only exist behind explicit Apply function.
assert "U.apply.onclick" in text
assert "confirm(" in text
# No attachment download endpoints/actions.
for forbidden in ['/backend-api/files/download/','/interpreter/download?','fetchAttachmentBinary','appendAttachmentsTo']:
    assert forbidden not in text, forbidden
# Optional online complement may only fetch conversation detail.
assert '/backend-api/conversation/${encodeURIComponent(conversationId)}' in text
# Apply safety: only provenance fields are stripped for invariant comparison.
for field in ['owner_role','source_category','reference_kind']:
    assert f'delete asset.{field}' in text
    assert f'delete failure.{field}' in text
assert 'attachment_state =' not in text
assert 'attachment_failures =' not in text
print('PASS provenance backfill 0.1.1 dry-run-first, explicit apply, backup and invariant guards')
