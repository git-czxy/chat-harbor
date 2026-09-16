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
    "syncSelectedBtn.onclick=runSync",
    "selectAllCheckbox.indeterminate",
    "当前匹配中",
    "未归档",
    "已归档",
    "重新扫描本地",
    "等待远端列表…",
    "按选择范围开始流式核验与写入",
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
    "{ countdown: true }",
    "onItemClassified",
    "onItemCommitted",
    "核验并同步",
    "await chApplyClassifiedSyncItem",
]:
    assert marker in core, f'missing runtime marker: {marker}'

assert '0.0.9.2' in source
assert "const FAB_STORAGE_KEY = 'chatharbor-fab-v1';" in source
assert 'background: #10a37f;' in source
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
assert "await loadAccountUniverse(false)" in picker
assert "await loadRemoteList();" not in picker.split("spaceSelect.onchange=async e=>",1)[1].split("projectSelect.onchange",1)[0]
assert "loadRemoteList(true)" in picker
assert "state.list = state.mode === 'project' ? all.filter(item => item.projectId || item.projectTitle) : all;" in picker
assert "const verifyCount = Math.max(0, (s.maximumFetchRequired || 0) - (s.newCount || 0));" in picker
assert "ch-result-panel" not in values['preflight_report_block'] or "style.display = 'none'" in values['preflight_report_block']
print('PASS cached canonical account index + local all/project scope switching')
print('PASS compact archive summary + sticky action rail markers')
print('PASS pending label refined to To process / 待处理')

print('PASS injected JavaScript syntax')
print('PASS single selection scope + tri-state select-all')
print('PASS canonical project metadata + unknown/none distinction markers')
print('PASS archive badges/default-all markers')
print('PASS auto local scan + rescan UI markers')
print('PASS streaming verify -> commit runtime markers')
print('PASS absolute-deadline sleep/wake reconciliation markers')
print('CORE_SHA256', hashlib.sha256(core.encode()).hexdigest())

assert '下一批前暂停约' not in core
assert '剩余 ${chFormatRemainingDuration(remaining)}' in core
print('PASS live MM:SS batch-pause countdown markers')
