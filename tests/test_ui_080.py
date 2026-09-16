import ast
import hashlib
import pathlib
import subprocess
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[1]
PATCHER = ROOT / 'ChatHarbor_IntegratedSync_patch.py'
OLD_PATCHER = pathlib.Path('/mnt/data/chatharbor_ui_080/chatharbor_integrated_sync_070/ChatHarbor_IntegratedSync_patch.py')
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
required = set(['directory_writer','single_page_picker','inline_report_helpers','preflight_report_block','integrated_report_block'])
assert required <= values.keys(), required - values.keys()
expected_core_hash = 'f4c01a1e3c2f94e3572fe76d1263f0c4ab3ea29a3c64b121482b6b2eab6122cc'
assert hashlib.sha256(values['directory_writer'].encode()).hexdigest() == expected_core_hash

picker = values['single_page_picker']
for marker in [
    "width: 'min(1240px, calc(100vw - 48px))'",
    "grid-template-columns:minmax(0,1fr) 310px",
    'id="ch-space-select"',
    'id="filter-project"',
    'id="filter-sync-status"',
    'id="preflight-plan-btn"',
    'id="sync-directory-btn"',
    'id="sync-filtered-btn"',
    'id="sync-all-btn"',
    'id="ch-pause-sync-btn"',
    'id="ch-cancel-sync-btn"',
    'id="ch-result-panel"',
    "archived: 'active'",
    "state.syncStatus='pending'",
    'e.shiftKey',
    "showDirectoryPicker({mode:'readwrite'})",
]:
    assert marker in picker, f'missing picker marker: {marker}'

for label in ['新增','待核验','内容更新','仅改名','更新+改名','仅元数据','已同步','异常']:
    assert label in picker, f'missing status label {label}'

assert "showExportDialog();" not in picker
assert 'ch-integrated-sync-report-overlay' not in values['integrated_report_block']
assert 'ch-preflight-report-overlay' not in values['preflight_report_block']
assert '复制详细报告' in values['inline_report_helpers']

for marker in [
    "const FAB_STORAGE_KEY = 'chatharbor-fab-v1';",
    'background: #10a37f;',
    'fabCollapseTimer = setTimeout',
    "showDialog: () => showConversationPicker",
    '0.0.8.0',
]:
    assert marker in source, f'missing launcher/runtime marker: {marker}'

# The sync/runtime core literal must be byte-for-byte identical to 0.0.7.0.
def literal(path, name):
    t = ast.parse(path.read_text(encoding='utf-8'))
    for n in t.body:
        if isinstance(n, ast.Assign) and len(n.targets)==1 and isinstance(n.targets[0], ast.Name) and n.targets[0].id == name:
            return ast.literal_eval(n.value)
    raise AssertionError(name)
if OLD_PATCHER.exists():
    old_core = literal(OLD_PATCHER, 'directory_writer')
    assert old_core == values['directory_writer']
    print('PASS sync/runtime core literal unchanged from 0.0.7.0')

# Compile every injected JavaScript block with Node.
for name in ['single_page_picker','inline_report_helpers','preflight_report_block','integrated_report_block']:
    with tempfile.NamedTemporaryFile('w', suffix='.js', delete=False, encoding='utf-8') as f:
        f.write(values[name])
        path = f.name
    subprocess.run(['node','--check',path],check=True,capture_output=True,text=True)
print('PASS injected JavaScript syntax')
print('PASS desktop single-page layout markers')
print('PASS right-rail progress/report architecture')
print('PASS sync status/filter/shift-selection markers')
print('PASS green persisted half-hide launcher markers')
print('CORE_SHA256', hashlib.sha256(values['directory_writer'].encode()).hexdigest())
