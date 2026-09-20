import pathlib, re, subprocess

ROOT = pathlib.Path(__file__).resolve().parents[1]
artifact = ROOT / 'ChatHarbor.user.js'
assert artifact.exists(), artifact
text = artifact.read_text(encoding='utf-8')
subprocess.run(['node','--check',str(artifact)], check=True, capture_output=True, text=True)


# Public release metadata
for marker in [
    '// @name         ChatHarbor',
    '// @author       git-czxy',
    '// @namespace    https://github.com/git-czxy/chat-harbor',
    '// @homepageURL  https://github.com/git-czxy/chat-harbor',
    '// @source       https://github.com/git-czxy/chat-harbor',
    '// @downloadURL  https://raw.githubusercontent.com/git-czxy/chat-harbor/main/ChatHarbor.user.js',
    '// @updateURL    https://raw.githubusercontent.com/git-czxy/chat-harbor/main/ChatHarbor.user.js',
    'Portions derived from huhusmang/ChatGPT-Exporter (MIT).'
]:
    assert marker in text, marker
for forbidden in [
    '@author       huhu; ChatHarbor contributors',
    '@namespace    https://github.com/huhusmang/ChatGPT-Exporter',
    'update.greasyfork.org/scripts/556233',
    'ChatGPT Exporter v1.5.0'
]:
    assert forbidden not in text, forbidden

# Version / inherited report baseline
assert re.search(r'^// @version\s+0\.0\.14\.5\s*$', text, re.M)
assert "const CH_PRODUCT_VERSION = '0.0.14.5';" in text
for marker in [
    'SYNC_COMPLETION','LOCAL_PREFLIGHT','run_started_at','run_finished_at',
    'scan_started_at','scan_finished_at','chFormatLocalTimestamp','getTimezoneOffset',
    "policy: 'excluded'","policy: 'new_or_unattempted_only'","policy: 'include_known_failures'",
    '当前处理会话中的附件引用总数','本轮附件失败原因','本轮附件失败明细'
]:
    assert marker in text, marker
assert '检测附件引用:' not in text

# Provenance model
for marker in [
    "'user_upload'","'assistant_generated_deliverable'","'generated_media'",
    "'assistant_asset'","'unknown'",'source_category','reference_kind','owner_role'
]:
    assert marker in text, marker
assert "if (role === 'user') return 'user_upload';" in text
assert "if (refKind === 'sandbox' && (role === 'assistant' || !role)) return 'assistant_generated_deliverable';" in text
assert "if (role === 'tool' && isImage) return 'generated_media';" in text
assert "if (role === 'assistant' || role === 'tool') return 'assistant_asset';" in text
assert "return 'unknown';" in text

# Conversation-centric UI, compact drill-down, original chat navigation
for marker in [
    'filter-attachment-integrity','附件：有未归档','未归档','查看这个会话中未成功归档的附件',
    '打开原会话','ch-attachment-detail-overlay','Everything','URL失效','当前未成功归档'
]:
    assert marker in text, marker
assert "https://chatgpt.com/c/${encodeURIComponent(item.id)}" in text

# Error interpretation remains separate from raw evidence
for code in ['403','404','415','500']:
    assert f"'{code}': chT(" in text
assert 'download_url' in text and 'missing or expired' in text
assert '原始错误' in text

# Historical provenance reconstruction must NOT live in normal planner/sync core.
assert 'chHydrateLocalAttachmentProvenance' not in text
assert 'chSummarizeLocalAttachmentProvenance(localScan);' in text
# Normal summary must not read local JSON merely to reconstruct provenance.
summary_start = text.index('function chSummarizeLocalAttachmentProvenance')
summary_end = text.index('function chAttachmentReferenceKey', summary_start)
summary_block = text[summary_start:summary_end]
assert 'chReadExistingText' not in summary_block
assert 'collectVisibleAttachments' not in summary_block

# Provenance is explanatory only: attachment action policy remains based on attachment state/failure ledger.
needs_start = text.index('function chAttachmentNeedsAction')
needs_end = text.index('\n    function ', needs_start + 20)
needs_block = text[needs_start:needs_end]
assert 'source_category' not in needs_block
assert 'owner_role' not in needs_block
assert 'reference_kind' not in needs_block
assert 'retryFailedAttachments' in needs_block

# Prior project-truth blocker stays fixed.
assert 'if(!resolved)return [];' not in text
assert 'accountIdentityResolved' in text and 'projectConversations' in text

# Four-state model still present.
for label in ['SYNCED','PENDING','CONFIRM','ERROR']:
    assert label in text
assert "SYNCED: chT('已同步'" in text

print('PASS 0.0.14.5 static contract: provenance, conversation UI, reports, core boundaries')
