import ast
import pathlib
import subprocess
import tempfile

ROOT=pathlib.Path(__file__).resolve().parents[1]
patch=(ROOT/'ChatHarbor_IntegratedSync_patch.py').read_text(encoding='utf-8')
prepare=(ROOT/'prepare_clean_integrated_sync.ps1').read_text(encoding='utf-8')
assert '// @version      0.0.14.1' in patch
assert 'ChatHarbor-IntegratedSync-0.0.14.1.user.js' in prepare
assert "chatharbor_network_policy_v2" in patch
assert "大量任务（更稳）" in patch and "保守模式（最稳）" in patch
assert "batchSize: 10" in patch and "batchPauseMinSec: 120" in patch and "batchPauseMaxSec: 180" in patch
assert "CH_ATTACHMENT_META_BASE_MS = 3000" in patch
assert "CH_ATTACHMENT_META_BATCH_SIZE = 10" in patch
assert "return 300000 * n" in patch
assert "chRegisterRateLimit" in patch
assert "chatharbor-directory-handle-v1" in patch
assert "LOCAL_UNTRACKED'\n    ]);" not in patch  # not a final auto-write action
assert 'fetch(`/backend-api/' in patch
assert 'text = text.replace("await fetch(`/backend-api/", "await chBackendFetch(`/backend-api/")' in patch

# Parse injected blocks and syntax-check them.
tree=ast.parse(patch)
blocks={}
for node in ast.walk(tree):
    if isinstance(node,ast.Assign) and len(node.targets)==1 and isinstance(node.targets[0],ast.Name):
        if node.targets[0].id in {'directory_writer','single_page_picker','inline_report_helpers','preflight_report_block','integrated_report_block'}:
            try: blocks[node.targets[0].id]=ast.literal_eval(node.value)
            except Exception: pass
assert set(blocks)=={'directory_writer','single_page_picker','inline_report_helpers','preflight_report_block','integrated_report_block'}
for name,code in blocks.items():
    with tempfile.NamedTemporaryFile('w',suffix='.js',delete=False,encoding='utf-8') as f:
        f.write(code); tmp=f.name
    subprocess.run(['node','--check',tmp],check=True,capture_output=True,text=True)

core=blocks['directory_writer']
picker=blocks['single_page_picker']
for marker in [
    'const chBackendScheduler', 'CH_BACKEND_LANE_DISCOVERY', 'CH_BACKEND_LANE_DETAIL', 'CH_BACKEND_LANE_ATTACHMENT',
    '请求过多，暂时休息', '服务器暂时出错（', 'CH_ATTACHMENT_META_BATCH_SIZE = 10', 'chRegisterRateLimit',
    'const chRuntimeProgress', '会话进度 ${done} / ${chRuntimeProgress.total}',
    'chDirectoryHandleLoad', 'chDirectoryHandleSave', "action:'LOCAL_UNTRACKED'", 'requires_user_confirmation:true',
    "record.attachment_state = 'partial'", 'onItemFailed', 'partial-root', 'partial-projects'
]:
    assert marker in core, marker
for marker in ['userStatus = value =>', "SYNCED: chT('已同步'", "PENDING: chT('待同步'", "CONFIRM: chT('需确认'", "ERROR: chT('异常'", 'restoreSavedRoot()', '!state.rootHandle || state.selected.size===0', '全选当前结果', '第一步：选择本地保存位置', '选择保存位置后可同步', '云端对话已加载']:
    assert marker in picker, marker
print('PASS 0.0.14.1 release invariants + injected JS syntax')
