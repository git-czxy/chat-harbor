import ast
import pathlib
import subprocess
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[1]
source = (ROOT / 'ChatHarbor_IntegratedSync_patch.py').read_text(encoding='utf-8')
tree = ast.parse(source)
core = None
for node in ast.walk(tree):
    if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name) and node.targets[0].id == 'directory_writer':
        core = ast.literal_eval(node.value)
        break
assert core

harness = r'''
globalThis.window = { fetch: async () => ({ ok:true, status:200 }), addEventListener: () => {} };
globalThis.document = { addEventListener: () => {}, hidden: false, getElementById: () => null };
globalThis.performance = { now: () => Date.now() };
globalThis.localStorage = { getItem: () => null, setItem: () => {} };
globalThis.navigator = { language: 'zh-CN' };
globalThis.location = { origin: 'https://chatgpt.com' };
globalThis.Request = class Request { constructor(url){ this.url=url; } };
globalThis.sleep = async () => {};
'''
checks = r'''
function assert(cond, msg){ if(!cond) throw new Error(msg); }
assert(chBackendLaneFor('/backend-api/conversations?offset=0') === CH_BACKEND_LANE_DISCOVERY, 'root list lane');
assert(chBackendLaneFor('/backend-api/gizmos/ws/conversations?cursor=0') === CH_BACKEND_LANE_DISCOVERY, 'project lane');
assert(chBackendLaneFor('/backend-api/files/download/file-1?inline=false') === CH_BACKEND_LANE_ATTACHMENT, 'file metadata lane');
assert(chBackendLaneFor('/backend-api/conversation/abc/interpreter/download?x=1') === CH_BACKEND_LANE_ATTACHMENT, 'sandbox metadata lane');
assert(chBackendLaneFor('/backend-api/conversation/abc') === CH_BACKEND_LANE_DETAIL, 'conversation detail lane');
const p = chNormalizeNetworkPolicy(CH_DEFAULT_NETWORK_POLICY);
const oldRandom = Math.random;
Math.random = () => 0;
assert(chLaneDelayMs(CH_BACKEND_LANE_DISCOVERY,p) === 600, 'discovery cadence');
assert(chLaneDelayMs(CH_BACKEND_LANE_ATTACHMENT,p) === 1500, 'attachment metadata cadence');
assert(chLaneDelayMs(CH_BACKEND_LANE_DETAIL,p) === 6000, 'detail cadence');
assert(chRetryDelayForFailure({status:500,lane:CH_BACKEND_LANE_DISCOVERY,attempt:1}) === 5000, 'discovery 5xx short retry');
assert(chRetryDelayForFailure({status:503,lane:CH_BACKEND_LANE_DETAIL,attempt:2}) === 30000, 'detail 5xx retry');
assert(chRetryDelayForFailure({status:500,lane:CH_BACKEND_LANE_ATTACHMENT,attempt:2}) === 10000, 'attachment metadata 5xx short retry');
assert(chRetryDelayForFailure({status:500,lane:CH_BACKEND_LANE_ATTACHMENT,attempt:2,binary:true}) === 20000, 'binary 5xx retry');
assert(chRetryDelayForFailure({status:401,lane:CH_BACKEND_LANE_DETAIL,attempt:1}) === null, '401 no retry');
assert(chRetryDelayForFailure({status:403,lane:CH_BACKEND_LANE_DETAIL,attempt:1}) === null, '403 no retry');
assert(chRetryDelayForFailure({status:404,lane:CH_BACKEND_LANE_ATTACHMENT,attempt:1}) === null, '404 no retry');
assert(chRetryDelayForFailure({status:429,lane:CH_BACKEND_LANE_DISCOVERY,attempt:2}) === 240000, '429 global cooldown retained');
chBackendContext.detailTitle = '退运邮件清点系统';
assert(chBackendRequestDescriptor('/backend-api/conversation/abc', CH_BACKEND_LANE_DETAIL).includes('退运邮件清点系统'), 'detail retry label includes title');
chBackendContext.attachmentName = 'report.zip';
assert(chBackendRequestDescriptor('/backend-api/files/download/file-1', CH_BACKEND_LANE_ATTACHMENT).includes('report.zip'), 'attachment retry label includes name');
chBackendContext.detailTitle = null; chBackendContext.attachmentName = null;
assert(chRetryPrimary(500) === '服务端错误（HTTP 500）', '5xx is service error, not network error');
chBackendScheduler.laneRequestCount.discovery = 19;
chBackendScheduler.laneRequestCount.detail = 19;
const t0 = Date.now();
chAfterBackendAttempt(p, CH_BACKEND_LANE_DISCOVERY);
assert(chBackendScheduler.laneNextAllowedAt.discovery - t0 < 2000, 'discovery must not inherit batch pause');
chAfterBackendAttempt(p, CH_BACKEND_LANE_DETAIL);
assert(chBackendScheduler.laneNextAllowedAt.detail - t0 >= 179000, 'detail batch pause required');
Math.random = oldRandom;
console.log('PASS lane classification + independent cadence + detail-only batch pause');
console.log('PASS typed HTTP failure policy + request-context retry labels');
'''

with tempfile.NamedTemporaryFile('w', suffix='.js', delete=False, encoding='utf-8') as f:
    f.write(harness)
    f.write('\n')
    f.write(core)
    f.write('\n')
    f.write(checks)
    path = f.name
res = subprocess.run(['node', path], text=True, capture_output=True)
if res.returncode != 0:
    raise SystemExit(res.stdout + res.stderr)
print(res.stdout.strip())
