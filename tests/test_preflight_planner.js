const fs = require('fs');
const assert = require('assert');

const CH_MANIFEST_NAME = 'ChatHarbor_manifest.json';
const CH_MANIFEST_SCHEMA_VERSION = 1;
const CH_SIGNATURE_VERSION = 'sha256-current_node+mapping-v1';
function normalizeEpochSeconds(value) {
  if (!value) return 0;
  if (typeof value === 'number' && Number.isFinite(value)) return value > 1e12 ? Math.floor(value / 1000) : value;
  if (typeof value === 'string') {
    const parsed = Date.parse(value);
    if (!Number.isNaN(parsed)) return Math.floor(parsed / 1000);
  }
  return 0;
}
let mockProjectList = [];
let mockRootList = [];
async function listProjectSpaceConversations(){ return mockProjectList; }
async function listConversations(){ return mockRootList; }
global.document={getElementById:()=>null};
global.localStorage={getItem:()=>null,setItem:()=>{}};
const snippet = fs.readFileSync(require('path').join(__dirname,'integrated_sync_layer.js'),'utf8');
eval(snippet);

function rec(id,title,t,tracking='manifest') {
  return {conversation_id:id,title,remote_update_time:t,tracking,json_path:`${id}.json`};
}

// Planner classification matrix.
const recordsById = new Map([
  ['A', rec('A','A',100)],
  ['B', rec('B','Old B',100)],
  ['C', rec('C','C',100)],
  ['D', rec('D','Old D',100)],
  ['I', rec('I','I',100,'raw_only')],
  ['G', rec('G','G',100)],
  ['H', rec('H','H',100,'duplicate_raw')],
]);
const localScan = {
  recordsById,
  duplicateIds:new Set(['H']),
  duplicates:[{id:'H',source:'local',paths:['h1.json','h2.json']}],
  blockedIds:new Set(['H']),
  errors:[],
  errorsById:new Map(),
  stats:{manifestTracked:5,rawConversationFiles:8,rawOnlyIds:1}
};
const remote = [
  {id:'A',title:'A',update_time:100},
  {id:'B',title:'New B',update_time:100},
  {id:'C',title:'C',update_time:101},
  {id:'D',title:'New D',update_time:101},
  {id:'E',title:'E',update_time:100},
  {id:'I',title:'I',update_time:100},
  {id:'H',title:'H',update_time:100},
  {id:'F',title:'F1',update_time:100},
  {id:'F',title:'F2',update_time:100},
];
const plan = chBuildPreflightPlan(remote, localScan);
assert.deepStrictEqual(plan.summary, {
  remote:9, remoteUnique:8, scopeRemote:8, local:7,
  newCount:1, remoteUpdateCandidateCount:2, renameCandidateCount:2,
  unchangedCount:1, metadataCandidateCount:0, rawOnlyVerifyCount:1, localOnlyCount:1, localOnlyReliable:true, remoteUniverseComplete:true, remoteUniverseNote:null, duplicateIdCount:2,
  errorCount:0, maximumFetchRequired:5,
  manifestTracked:5, rawConversationFiles:8, rawOnlyIds:1
});
assert.strictEqual(plan.items.find(x=>x.id==='A').action,'UNCHANGED');
assert.strictEqual(plan.items.find(x=>x.id==='B').action,'VERIFY_RENAMED');
assert.strictEqual(plan.items.find(x=>x.id==='C').action,'VERIFY_CHANGED');
assert.strictEqual(plan.items.find(x=>x.id==='D').action,'VERIFY_CHANGED');
assert.strictEqual(plan.items.find(x=>x.id==='E').action,'NEW');
assert.strictEqual(plan.items.find(x=>x.id==='I').action,'VERIFY_CHANGED');
assert.strictEqual(plan.items.find(x=>x.id==='H').action,'DUPLICATE');
assert.strictEqual(plan.items.find(x=>x.id==='F').action,'DUPLICATE');
assert.deepStrictEqual(plan.localOnly.map(x=>x.id),['G']);

const selectedPlan = chBuildPreflightPlan(remote, localScan, new Set(['B','E']));
assert.strictEqual(selectedPlan.summary.scopeRemote,2);
assert.strictEqual(selectedPlan.summary.newCount,1);
assert.strictEqual(selectedPlan.summary.renameCandidateCount,1);
assert.strictEqual(selectedPlan.summary.maximumFetchRequired,2);
// LOCAL_ONLY must still be computed against the full remote set, not selection.
assert.deepStrictEqual(selectedPlan.localOnly.map(x=>x.id),['G']);
const incompletePlan = chBuildPreflightPlan(remote, localScan, null, {remoteUniverseComplete:false, remoteUniverseNote:'test partial'});
assert.strictEqual(incompletePlan.summary.localOnlyCount,null);
assert.strictEqual(incompletePlan.summary.localOnlyReliable,false);
assert.strictEqual(incompletePlan.localOnly.length,0);

(async()=>{
  mockProjectList=[{id:'P',title:'Project',update_time:1,projectId:'p',projectTitle:'P'}];
  const personalUniverse=await chCollectPreflightRemoteUniverse('personal',null,[{id:'R',title:'Root',update_time:1}]);
  assert.strictEqual(personalUniverse.complete,true);
  assert.strictEqual(personalUniverse.remoteList.length,2);
  mockRootList=[{id:'R',title:'Root',update_time:1}];
  const projectUniverse=await chCollectPreflightRemoteUniverse('project',null,[{id:'P',title:'Project',update_time:1,projectId:'p',projectTitle:'P'}]);
  assert.strictEqual(projectUniverse.complete,true);
  assert.strictEqual(projectUniverse.remoteList.length,2);
})();

const metadataScan = {
  recordsById:new Map([['M',{conversation_id:'M',title:'M',remote_update_time:100,is_archived:false,project_id:null,project_title:null,tracking:'manifest'}]]),
  duplicateIds:new Set(), duplicates:[], blockedIds:new Set(), errors:[], errorsById:new Map(),
  stats:{manifestTracked:1,rawConversationFiles:1,rawOnlyIds:0}
};
const metadataPlan = chBuildPreflightPlan([{id:'M',title:'M',update_time:100,is_archived:true,projectId:null,projectTitle:null}], metadataScan);
assert.strictEqual(metadataPlan.summary.metadataCandidateCount,1);
assert.strictEqual(metadataPlan.summary.maximumFetchRequired,1);
assert.strictEqual(metadataPlan.items[0].action,'VERIFY_CHANGED');
assert(metadataPlan.items[0].reasons.includes('ARCHIVE_STATE_DIFF'));

// Fake File System Access API handles for archive scanner tests.
class FakeFile {
  constructor(text){ this.kind='file'; this._text=text; }
  async getFile(){ return { text: async()=>this._text }; }
}
class FakeDir {
  constructor(entries={}){ this.kind='directory'; this._entries=new Map(Object.entries(entries)); }
  async *entries(){ for (const kv of this._entries) yield kv; }
  async getFileHandle(name){
    const h=this._entries.get(name);
    if (!h || h.kind!=='file') { const e=new Error('not found'); e.name='NotFoundError'; throw e; }
    return h;
  }
}
function conv(id,title='T',update=100){ return JSON.stringify({conversation_id:id,title,update_time:update,mapping:{node:{id:'node'}}}); }
const manifest = {
  schema_version:1,
  identity:'conversation_id',
  signature_version:'sha256-current_node+mapping-v1',
  conversations:{
    A:{conversation_id:'A',title:'A',remote_update_time:100,json_path:'A.json'},
    B:{conversation_id:'B',title:'B',remote_update_time:100,json_path:'missing.json'}
  }
};
const root = new FakeDir({
  [CH_MANIFEST_NAME]: new FakeFile(JSON.stringify(manifest)),
  'A.json': new FakeFile(conv('A','A')),
  'dup1.json': new FakeFile(conv('H','H')),
  'dup2.json': new FakeFile(conv('H','H2')),
  'I.json': new FakeFile(conv('I','I')),
  'misc.json': new FakeFile(JSON.stringify({hello:'world'})),
  'broken.json': new FakeFile('{not json'),
  'sample_files': new FakeDir({
    // Intentionally conversation-shaped: it must be ignored because *_files is asset storage.
    'asset.json': new FakeFile(conv('SHOULD_NOT_SCAN','asset'))
  })
});
(async()=>{
  const scan=await chScanLocalArchiveReadOnly(root);
  assert.strictEqual(scan.manifestExists,true);
  assert.strictEqual(scan.manifestReadable,true);
  assert.strictEqual(scan.stats.local,4); // A,B,H,I
  assert.strictEqual(scan.stats.manifestTracked,2);
  assert.strictEqual(scan.stats.rawConversationFiles,4); // A,H,H,I
  assert.strictEqual(scan.stats.rawUniqueIds,3); // A,H,I
  assert.strictEqual(scan.stats.rawOnlyIds,1); // I only; H is duplicate
  assert.strictEqual(scan.stats.ignoredJsonFiles,2); // misc + broken
  assert.strictEqual(scan.stats.skippedAssetDirs,1);
  assert.deepStrictEqual(scan.duplicates.map(x=>x.id),['H']);
  assert(scan.blockedIds.has('H'));
  assert(scan.blockedIds.has('B'));
  assert(scan.errors.some(e=>e.type==='MANIFEST_JSON_NOT_FOUND' && e.id==='B'));
  assert(!scan.recordsById.has('SHOULD_NOT_SCAN'));
  console.log('PASS planner classification matrix');
  console.log('PASS selective-scope LOCAL_ONLY safety');
  console.log('PASS read-only archive scan duplicate/error/_files handling');
  console.log('SUMMARY', JSON.stringify(plan.summary));
})().catch(e=>{console.error(e);process.exit(1)});
