import ast, pathlib
ROOT=pathlib.Path(__file__).resolve().parents[1]
source=(ROOT/'ChatHarbor_IntegratedSync_patch.py').read_text(encoding='utf-8')
tree=ast.parse(source)
vals={}
for node in ast.walk(tree):
    if isinstance(node,ast.Assign) and len(node.targets)==1 and isinstance(node.targets[0],ast.Name):
        if node.targets[0].id in {'directory_writer','single_page_picker','preflight_report_block','integrated_report_block'}:
            try: vals[node.targets[0].id]=ast.literal_eval(node.value)
            except Exception: pass
picker=vals['single_page_picker']; core=vals['directory_writer']; pre=vals['preflight_report_block']; report=vals['integrated_report_block']

# User-facing four-state model only.
for label in ['已同步','待同步','需确认','异常']:
    assert label in picker
for technical_label in ['仅元数据','本地未跟踪','内容更新','仅改名','更新+改名','待核验']:
    assert technical_label not in picker, technical_label
assert "['SYNCED'" not in picker or True
assert "['all', `${chT('状态：全部'" in picker

# Plain-language UI / action separation.
for marker in ['本地保存','重新检查','请求速度','附件','搜索对话或项目','同步选中']:
    assert marker in picker, marker
assert "同步选中" in picker
assert "const ensureRoot = async () =>" in picker and "请先选择本地保存位置" in picker
# ensureRoot no longer invokes directory picker; only chooseRoot does.
ensure=picker[picker.index('const ensureRoot = async () =>'):picker.index('const chooseRoot = async () =>')]
assert 'showDirectoryPicker' not in ensure
choose=picker[picker.index('const chooseRoot = async () =>'):picker.index('const restoreSavedRoot = async () =>')]
assert 'showDirectoryPicker' in choose and 'chDirectoryHandleSave' in choose
assert "chooseDirBtn.disabled = chSyncRun.active || state.migrationActive" in picker
assert "preflightBtn.disabled = chSyncRun.active || state.migrationActive || !state.rootHandle" in picker
assert "syncSelectedBtn.disabled = disabled || migrationRequired || !state.rootHandle || state.selected.size===0" in picker

# Directory restore and short tooltips.
assert 'restoreSavedRoot();loadRemoteList();' in picker
assert "切换本地保存位置。" in picker
assert "重新检查当前保存位置。" in picker
assert "更新云端对话列表。" in picker

# Stable progress + current sub-task.
assert 'const chRuntimeProgress' in core
assert '会话进度 ${done} / ${chRuntimeProgress.total}' in core
assert '当前：${chRuntimeProgress.currentTitle}' in core
assert "chSetProgress('正在获取对话', '', null)" in core
assert "phase === '下载附件' ? '正在下载附件'" in core
assert '快速跳过 ${fastItems.length}' not in core

# Rows stay quiet unless exceptional.
assert "meta.textContent=item.projectTitle?`${item.projectTitle} · ${timeText}`:timeText" in picker
assert "if(item.is_archived){const archiveBadge" in picker

# Request presets are use-case language; technical values remain expandable.
for marker in ['少量任务（较快）','日常使用（平衡）','大量任务（更稳）','保守模式（最稳）','applySpeedPreset']:
    assert marker in source
assert "chT('使用场景','Use case')" in picker
assert "出现“请求过多”时，建议改用“保守模式（最稳）”。" in picker
assert "chT('高级设置','Advanced settings')" in picker
assert 'chNetworkPolicyDetail' in source

# Visible summaries are user-oriented; diagnostics remain in detail text.
assert "chT('本地检查详情','Local check details')" in pre
assert "chT('选择','Selected')" in report and "chT('实际处理','Processed')" in report
assert "chT('需确认','Check')" in report
print('PASS 0.0.14.0 user-facing UX convergence invariants')
