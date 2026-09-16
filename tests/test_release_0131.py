import ast
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
patch=(ROOT/'ChatHarbor_IntegratedSync_patch.py').read_text(encoding='utf-8')
prepare=(ROOT/'prepare_clean_integrated_sync.ps1').read_text(encoding='utf-8')
assert '// @version      0.0.13.1' in patch
assert 'ChatHarbor-IntegratedSync-0.0.13.1.user.js' in prepare
assert 'async function chBackendFetch' in patch
assert 'async function chDataTransferFetch' in patch
assert 'const chBackendScheduler' in patch
assert 'remoteRefreshPromise' in patch and 'pendingRemoteSnapshot' in patch
assert 'assetFastChecked' in patch and '__chAssetIntegrity' in patch
assert '__ch_new_asset_paths' in patch and 'priorManifestRecord' in patch
assert 'onItemFailed' in patch
assert 'fetch(`/backend-api/' in patch  # rewrite rule / forbidden marker lives in patcher source
# Release build fails closed if any direct backend control fetch survives generated text.
assert '"fetch(`/backend-api/"' in patch
assert '"fetch(metadataUrl' in patch
assert '"fetch(parsedUrl.href, sameOrigin"' in patch

# Compile the main injected runtime block independently.
tree=ast.parse(patch)
core=None
for node in ast.walk(tree):
    if isinstance(node,ast.Assign) and len(node.targets)==1 and isinstance(node.targets[0],ast.Name) and node.targets[0].id=='directory_writer':
        core=ast.literal_eval(node.value); break
assert core
assert 'API 限流（429）' in core
assert 'global HTTP 429 cooldown' in core
assert "record.attachment_state = 'partial'" in core
assert 'onItemFailed' in core
assert "CH_BACKEND_LANE_DISCOVERY" in core
assert "CH_BACKEND_LANE_DETAIL" in core
assert "CH_BACKEND_LANE_ATTACHMENT" in core
assert "laneRequestCount" in core and "laneNextAllowedAt" in core
assert "Batch pauses belong only to expensive conversation-detail traffic" in core
assert "Incomplete snapshots are still useful UI/discovery cache" in core
assert "partial-root" in core and "partial-projects" in core
assert "chSetNetworkStatusHook" in core

assert 'function chBackendRequestDescriptor' in core
assert 'function chRetryDelayForFailure' in core
assert '服务端错误（HTTP' in core
assert "status === 401 || status === 403 || status === 404" in core
assert 'chBackendContext.detailTitle' in core and 'chBackendContext.attachmentName' in core
assert '网络异常，保守重试等待' not in core
print('PASS 0.0.13.1 release/build invariants')
