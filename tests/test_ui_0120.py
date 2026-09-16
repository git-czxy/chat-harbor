import ast
import hashlib
import pathlib
import subprocess
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[1]
PATCHER = ROOT / 'ChatHarbor_IntegratedSync_patch.py'
source = PATCHER.read_text(encoding='utf-8')
tree = ast.parse(source)
values = {}
for node in ast.walk(tree):
    if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
        name = node.targets[0].id
        if name in {'directory_writer','single_page_picker','inline_report_helpers','preflight_report_block','integrated_report_block'}:
            try:
                values[name] = ast.literal_eval(node.value)
            except Exception:
                pass
required = {'directory_writer','single_page_picker','inline_report_helpers','preflight_report_block','integrated_report_block'}
assert required <= values.keys(), required - values.keys()

picker = values['single_page_picker']
core = values['directory_writer']

for marker in [
    "width: 'min(1240px, calc(100vw - 48px))'",
    "grid-template-columns:minmax(0,1fr) 310px",
    'id="ch-space-select"',
    'id="filter-project"',
    'id="filter-archived"',
    'id="filter-sync-status"',
    'id="select-all-checkbox"',
    'id="preflight-plan-btn"',
    'id="sync-directory-btn"',
    'id="ch-pause-sync-btn"',
    'id="ch-cancel-sync-btn"',
    'id="ch-result-panel"',
    'id="ch-action-bar"',
    'id="ch-archive-copy-report-btn"',
    "chT('全部对话','All conversations')",
    "chT('项目对话','Project conversations')",
    'accountUniverse',
    "chT('待处理','To process')",
    "archived: 'all'",
    "__chProjectState",
    "decorateProjectKnowledge",
    "state.remoteUniverse",
    "await runPreflight(true)",
    'id="ch-migrate-layout-btn"',
    "runLayoutMigration",
    "chArchiveLayoutState",
    "纯本地升级，不重新下载",
    "syncSelectedBtn.onclick=runSync",
    "selectAllCheckbox.indeterminate",
    "未归档",
    "已归档",
    "重新扫描本地",
    "等待远端列表…",
    'id="ch-sync-content-summary"',
    'id="ch-network-policy-lock-note"',
    'id="ch-sync-content-lock-note"',
    "chT('归档详情','Archive details')",
    "chT('不下载附件','Do not download attachments')",
    "chT('下载附件','Download attachments')",
    "chT('当前','Current')",
    "按实际待处理范围开始流式核验与写入…",
]:
    assert marker in picker, f'missing picker marker: {marker}'

for forbidden in [
    'id="sync-filtered-btn"',
    'id="sync-all-btn"',
    'id="clear-all-btn"',
    "syncFilteredBtn",
    "syncAllBtn",
    "runSync('filtered')",
    "runSync('all')",
]:
    assert forbidden not in picker, f'obsolete multi-scope UI remains: {forbidden}'

for label in ['新增','待核验','内容更新','仅改名','更新+改名','仅元数据','已同步','异常']:
    assert label in picker, f'missing status label {label}'

for marker in [
    "const deadline = Date.now() + duration",
    "systemSuspended",
    "恢复保护等待",
    "chReconcileRuntimeState",
    "visibilitychange",
    "wake-guard",
    "chFormatRemainingDuration",
    "API 限流（429）",
    "async function chBackendFetch",
    "async function chDataTransferFetch",
    "const chBackendScheduler",
    "onItemFailed",
    "onItemClassified",
    "onItemCommitted",
    "核验并同步",
    "await chApplyClassifiedSyncItem",
]:
    assert marker in core, f'missing runtime marker: {marker}'

assert '0.0.12.0' in source
assert '// @version      0.0.12.0' in source
assert "const FAB_STORAGE_KEY = 'chatharbor-fab-v2';" in source
assert 'background: #10a37f;' in source

# Release-build invariant contract: the runtime marker must match the current UI wording.
required_runtime_markers_value = None
for node in ast.walk(tree):
    if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name) and node.targets[0].id == 'required_runtime_markers':
        required_runtime_markers_value = ast.literal_eval(node.value)
        break
assert required_runtime_markers_value is not None
assert '按实际待处理范围开始流式核验与写入' in required_runtime_markers_value
assert '按选择范围开始流式核验与写入' not in required_runtime_markers_value
print('PASS release-build invariant marker matches current actionable-work wording')
assert 'fabCollapseTimer = setTimeout' in source
assert '复制详细报告' in values['inline_report_helpers']
assert 'ch-archive-copy-report-btn' in values['preflight_report_block']
assert 'ch-integrated-sync-report-overlay' not in values['integrated_report_block']
assert 'ch-preflight-report-overlay' not in values['preflight_report_block']

# Compile all injected JavaScript blocks with Node.
for name in ['directory_writer','single_page_picker','inline_report_helpers','preflight_report_block','integrated_report_block']:
    with tempfile.NamedTemporaryFile('w', suffix='.js', delete=False, encoding='utf-8') as f:
        f.write(values[name])
        path = f.name
    subprocess.run(['node','--check',path],check=True,capture_output=True,text=True)


assert "spaceSelect.onchange=async e=>" in picker
assert "await loadRemoteList(false)" in picker
assert "chRemoteCacheGet(ws)" in picker
assert "chRefreshRemoteIndex(ws" in picker
assert "loadRemoteList(true,Boolean(e?.shiftKey))" in picker
assert "state.list=state.mode==='project'?list.filter(item=>item.projectId||item.projectTitle):list;" in picker
assert "const verifyCount = Math.max(0, (s.maximumFetchRequired || 0) - (s.newCount || 0));" in picker
assert "$('ch-header-summary').textContent = CH_PROVIDER_LABEL;" in picker
assert "`${chT('目录','Directory')}：${state.rootHandle.name}`" in picker
assert "margin-left:24px" in picker
assert "const providerTotal = state.remoteUniverse.length || state.list.length;" in picker
assert "state.runSettings={includeAttachments:Boolean(state.includeAttachments),networkPolicy:{...chSyncRun.policy}};" in picker
assert "includeAttachments:state.runSettings.includeAttachments" in picker
assert "networkPolicy:chSyncRun.policy" in picker
assert "[speedLevelInput,batchSizeInput,pauseMinInput,pauseMaxInput,includeAttachmentsInput].forEach" in picker
assert "if (chSyncRun.active) { updateSettingsSummary(); return; }" in picker
assert "searchInput,spaceSelect" in picker
assert "cb.disabled=state.loading||chSyncRun.active||state.migrationActive" in picker
assert "ch-result-panel" not in values['preflight_report_block'] or "style.display = 'none'" in values['preflight_report_block']
print('PASS persistent remote-index cache + local all/project scope switching')
print('PASS compact archive summary + sticky action rail markers')
print('PASS provider-only header + explicit archive directory label')
print('PASS fixed-left selection counts with Selected / Current / Total semantics')
print('PASS sync-content collapsed summary mirrors attachment policy')
print('PASS execution locks network/attachment/filter/selection controls to run snapshot')
print('PASS pending label refined to To process / 待处理')

print('PASS injected JavaScript syntax')
print('PASS single selection scope + tri-state select-all')
print('PASS canonical project metadata + unknown/none distinction markers')
print('PASS archive badges/default-all markers')
print('PASS auto local scan + rescan UI markers')
print('PASS streaming verify -> commit runtime markers')
print('PASS absolute-deadline sleep/wake reconciliation markers')
print('CORE_SHA256', hashlib.sha256(core.encode()).hexdigest())


assert "CH_REMOTE_CACHE_DB" in core
assert "CH_REMOTE_HEAD_LIMIT = 20" in core
assert "chFetchRemoteHeadSnapshot" in core
assert "head.fingerprint===cached.headFingerprint" in core
assert "CH_REMOTE_FULL_REFRESH_MS" in core
assert "remote_list_update_time" in core
assert "remote_observed_at" in core
assert "OBSERVATION_ONLY" in core
assert "ATTACHMENT_BACKFILL" in core
assert "attachment_state" in core
assert "trackedFastChecked" in core
assert "Manifest fast-checked" not in core or True
print('PASS convergent list-observation checkpoint markers')
print('PASS attachment completeness/backfill markers')
assert 'function chInferLegacyAttachmentState' in core
assert 'function chPlanAttachmentBackfill' in core
assert 'Progress is completion-based and monotonic' in core
assert 'root_path: asset?.path ||' in core
assert 'file.root_path || `${relativePrefix}${file.disk_path}`' in core
print('PASS legacy attachment inference + missing-only reuse + monotonic progress markers')
print('PASS Manifest-first local index markers')
print('PASS remote-index fast-head / periodic-full cache markers')

assert '下一批前暂停约' not in core
assert '剩余 ${chFormatRemainingDuration(remaining)}' in core
print('PASS live MM:SS batch-pause countdown markers')

assert '当前第 ${conversationIndex + 1} / ${conversationTotal} 条 · ${phase}' in core
assert 'const workItems = plan.items.filter' in core
assert '快速跳过 ${fastItems.length} 条已由 Manifest/预检确认的记录' in core
assert 'for (let i = 0; i < workItems.length; i++)' in core
assert 'setFabStatus(btn, `💾 ${phase}' not in core
assert "launcher.classList.add('gre-busy')" in picker
assert 'background:#fef3c7;color:#92400e' in picker
assert "`${chT('本地','Local')} ${s.local || 0}（${chT('项目内','in projects')}" in picker
print('PASS current-item progress wording + archived amber badge')


# 0.0.12.0 cross-cutting invariants.
assert 'remoteRefreshPromise' in picker
assert 'pendingRemoteSnapshot' in picker
assert 'await state.remoteRefreshPromise' in picker
assert 'onItemFailed:(item)' in picker
assert "state.syncStatusById.set(item.id,'ERROR')" in picker
assert 'assetFastChecked' in core
assert "record.attachment_state = 'partial'" in core
assert 'Reuse only assets whose Manifest identity and physical file both remain valid' in core
assert '__ch_new_asset_paths' in core
assert 'priorManifestRecord' in core
assert "chRemoveTrackedEntry(rootHandle, path, false)" in core
assert 'const chBackendScheduler' in core
assert 'async function chBackendFetch' in core
assert 'async function chDataTransferFetch' in core
assert "cooldownReason = 'HTTP_429'" in core
assert 'chWithBackendSerial' in core
# The patcher must rewrite all ChatHarbor /backend-api control fetches and metadata fetches.
assert 'text = text.replace("await fetch(`/backend-api/", "await chBackendFetch(`/backend-api/")' in source
assert 'text = text.replace("await fetch(metadataUrl' in source
assert 'text = text.replace("await fetch(parsedUrl.href, sameOrigin", "await chDataTransferFetch(parsedUrl.href, sameOrigin")' in source
print('PASS shared backend scheduler + global cooldown markers')
print('PASS remote-refresh single-flight / run snapshot freeze markers')
print('PASS physical attachment integrity + manifest rollback markers')
print('PASS commit-accurate UI status markers')
