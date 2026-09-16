const fs = require('fs');
const assert = require('assert');
const { webcrypto } = require('crypto');
global.crypto = webcrypto;
const CH_SIGNATURE_VERSION = 'sha256-current_node+mapping-v1';

function normalizeEpochSeconds(value) {
  if (!value) return 0;
  if (typeof value === 'number' && Number.isFinite(value)) return value > 1e12 ? Math.floor(value / 1000) : value;
  if (typeof value === 'string') { const p=Date.parse(value); return Number.isNaN(p)?0:Math.floor(p/1000); }
  return 0;
}
function sanitizeFilename(name){ return String(name||'').replace(/[\/\\?%*:|"<>]/g,'-').trim(); }
function generateUniqueFilename(c){ return `${sanitizeFilename(c.title||'Untitled')}_${(c.conversation_id||c.id||'id').split('-').pop()}.json`; }
function generateMarkdownFilename(c){ return generateUniqueFilename(c).replace(/\.json$/,'.md'); }
function chRemoteConversationId(e){ return String(e?.id||e?.conversation_id||''); }
function chTimeEquivalent(a,b){ const aa=normalizeEpochSeconds(a),bb=normalizeEpochSeconds(b); return !!aa&&!!bb&&Math.abs(aa-bb)<=0.001; }
function chGetConversationId(entry, convData){ return convData?.conversation_id||convData?.id||entry?.id||null; }
async function chContentSignature(c){ return c.__sig || 'sig'; }
function chExistingAttachmentResult(existingRecord){
  const assets=existingRecord?.assets||[]; return assets.length?{detected:assets.length,files:[],failures:[],sandboxPaths:new Map(),folderName:existingRecord.asset_dir,reusedExisting:true,sandboxSourceComplete:true}:null;
}
function chSetProgress(){}
async function ensureAccessToken(){return true;}
async function getConversation(){throw new Error('not stubbed');}
const sleep=async()=>{};
const jitter=()=>0;
function getExportButton(){return {};}
async function chWriteConversationToDirectory(){throw new Error('default writer should be mocked in transaction tests');}
async function chWriteManifest(){throw new Error('default manifest should be mocked in transaction tests');}
function chShowIntegratedSyncReport(){}
function chBuildPreflightPlan(){throw new Error('not used');}
async function chScanLocalArchiveReadOnly(){throw new Error('not used');}
async function chReadManifest(){throw new Error('not used');}

const layer=fs.readFileSync('/mnt/data/chatharbor_stage4/integrated_sync_layer.js','utf8');
eval(layer);

(async()=>{
  // Remote-universe merge must collapse discovery duplicates by canonical ID.
  const merged=chMergeRemoteEntries([
    {id:'A',title:'A',update_time:10},
    {id:'A',title:'A',update_time:10,projectId:'p',projectTitle:'P'},
    {id:'B',title:'B',update_time:9}
  ]);
  assert.strictEqual(merged.length,2);
  assert.strictEqual(merged.find(x=>x.id==='A').projectTitle,'P');

  const manifestLocal=(title='T',sig='same',time=100,extra={})=>({
    conversation_id:'X', title, content_signature:sig, remote_update_time:time, tracking:'manifest',
    is_archived:false, project_id:null, project_title:null, json_path:'T_X.json', markdown_path:'T_X.md', assets:[], ...extra
  });
  const baseItem=(local,remote={id:'X',title:'T',update_time:100,is_archived:false,projectId:null,projectTitle:null})=>({id:'X',remote,local});

  let r=await chClassifyFetchedConversation(baseItem(null),{conversation_id:'X',title:'T',update_time:100,__sig:'n'});
  assert.strictEqual(r.finalAction,'NEW');

  r=await chClassifyFetchedConversation(baseItem(manifestLocal('T','old')),{conversation_id:'X',title:'T',update_time:101,__sig:'new'});
  assert.strictEqual(r.finalAction,'UPDATED');

  r=await chClassifyFetchedConversation(baseItem(manifestLocal('Old','same'),{id:'X',title:'New',update_time:100,is_archived:false,projectId:null,projectTitle:null}),{conversation_id:'X',title:'New',update_time:100,__sig:'same'});
  assert.strictEqual(r.finalAction,'RENAMED_ONLY');

  r=await chClassifyFetchedConversation(baseItem(manifestLocal('Old','old'),{id:'X',title:'New',update_time:101,is_archived:false,projectId:null,projectTitle:null}),{conversation_id:'X',title:'New',update_time:101,__sig:'new'});
  assert.strictEqual(r.finalAction,'UPDATED_AND_RENAMED');

  r=await chClassifyFetchedConversation(baseItem(manifestLocal('T','same',100)),{conversation_id:'X',title:'T',update_time:101,__sig:'same'});
  assert.strictEqual(r.finalAction,'METADATA_ONLY');

  r=await chClassifyFetchedConversation(baseItem(manifestLocal('T','same',100),{id:'X',title:'T',update_time:100,is_archived:true,projectId:null,projectTitle:null}),{conversation_id:'X',title:'T',update_time:100,__sig:'same'});
  assert.strictEqual(r.finalAction,'METADATA_ONLY');

  r=await chClassifyFetchedConversation(baseItem(manifestLocal('T','same',100)),{conversation_id:'X',title:'T',update_time:100,__sig:'same'});
  assert.strictEqual(r.finalAction,'UNCHANGED');

  r=await chClassifyFetchedConversation(baseItem(manifestLocal('T','',100)),{conversation_id:'X',title:'T',update_time:101,__sig:'same'});
  assert.strictEqual(r.finalAction,'ERROR');
  assert(r.finalReasons.includes('LOCAL_SIGNATURE_MISSING'));

  r=await chClassifyFetchedConversation(baseItem({...manifestLocal(),tracking:'raw_only',content_signature:undefined}),{conversation_id:'X',title:'T',update_time:100,__sig:'same'});
  assert.strictEqual(r.finalAction,'LOCAL_UNTRACKED');
  assert.strictEqual(r.contentChanged,null);

  // Attachment links remain valid when Markdown relocates across project directories.
  assert.strictEqual(
    chRelativeMarkdownPath('New Project/','Old Project/T_files/a b.pdf'),
    '../Old%20Project/T_files/a%20b.pdf'
  );
  assert.strictEqual(
    chRelativeMarkdownPath('','Old Project/T_files/a b.pdf'),
    'Old%20Project/T_files/a%20b.pdf'
  );


  // Detail verification fetches only preflight candidates, never UNCHANGED/DUPLICATE items.
  const fetched=[];
  getConversation = async (id)=>{ fetched.push(id); return {conversation_id:id,title:id,update_time:101,__sig:id==='C'?'new':'same'}; };
  const verificationPlan={items:[
    {id:'A',action:'UNCHANGED',needs_detail_fetch:false,remote:{id:'A',title:'A',update_time:100},local:{...manifestLocal('A','same',100),conversation_id:'A'}},
    {id:'B',action:'NEW',needs_detail_fetch:true,remote:{id:'B',title:'B',update_time:101},local:null},
    {id:'C',action:'VERIFY_CHANGED',needs_detail_fetch:true,remote:{id:'C',title:'C',update_time:101},local:{...manifestLocal('C','old',100),conversation_id:'C'}},
    {id:'D',action:'DUPLICATE',needs_detail_fetch:false,remote:{id:'D',title:'D'},local:null,reasons:['REMOTE_DUPLICATE_ID']}
  ]};
  const verified=await chVerifyPreflightCandidates({plan:verificationPlan,workspaceId:null});
  assert.deepStrictEqual(fetched,['B','C']);
  assert.strictEqual(verified.detailFetchCount,2);
  assert.strictEqual(verified.items.find(x=>x.id==='A').finalAction,'UNCHANGED');
  assert.strictEqual(verified.items.find(x=>x.id==='B').finalAction,'NEW');
  assert.strictEqual(verified.items.find(x=>x.id==='C').finalAction,'UPDATED');
  assert.strictEqual(verified.items.find(x=>x.id==='D').finalAction,'DUPLICATE');

  // Transaction ordering: new files -> manifest commit -> cleanup old tracked paths.
  const order=[];
  const manifest={conversations:{X:{...manifestLocal('Old','same',100),json_path:'Old_X.json',markdown_path:'Old_X.md'}}};
  const classified={
    id:'X',finalAction:'RENAMED_ONLY',remote:{id:'X',title:'New',update_time:100},
    convData:{conversation_id:'X',title:'New',update_time:100,__sig:'same'},newSignature:'same'
  };
  const applied=await chApplyClassifiedSyncItem({
    rootHandle:{},classifiedItem:classified,manifest,workspaceId:null,includeAttachments:false,
    deps:{
      writeConversation:async()=>{order.push('write');return {...manifestLocal('New','same',100),conversation_id:'X',json_path:'New_X.json',markdown_path:'New_X.md'};},
      writeManifest:async()=>{order.push('manifest');},
      cleanup:async()=>{order.push('cleanup');return {removed:['Old_X.json'],warnings:[]};}
    }
  });
  assert.deepStrictEqual(order,['write','manifest','cleanup']);
  assert.strictEqual(applied.mode,'FILES_AND_MANIFEST');

  // Manifest failure must prevent cleanup.
  const order2=[];
  const manifest2={conversations:{X:{...manifestLocal('Old','same',100),json_path:'Old_X.json',markdown_path:'Old_X.md'}}};
  await assert.rejects(()=>chApplyClassifiedSyncItem({
    rootHandle:{},classifiedItem:classified,manifest:manifest2,
    deps:{
      writeConversation:async()=>{order2.push('write');return {...manifestLocal('New','same',100),conversation_id:'X',json_path:'New_X.json',markdown_path:'New_X.md'};},
      writeManifest:async()=>{order2.push('manifest');throw new Error('commit failed');},
      cleanup:async()=>{order2.push('cleanup');return {removed:[],warnings:[]};}
    }
  }));
  assert.deepStrictEqual(order2,['write','manifest']);

  // In-place metadata change must commit only manifest, not rewrite files.
  const order3=[];
  const localM={...manifestLocal('T','same',100),json_path:'T_X.json',markdown_path:'T_X.md'};
  const manifest3={conversations:{X:localM}};
  const metaItem={id:'X',finalAction:'METADATA_ONLY',remote:{id:'X',title:'T',update_time:101},convData:{conversation_id:'X',title:'T',update_time:101,__sig:'same'},newSignature:'same'};
  const metaApplied=await chApplyClassifiedSyncItem({
    rootHandle:{},classifiedItem:metaItem,manifest:manifest3,
    deps:{
      writeConversation:async()=>{order3.push('write');throw new Error('must not write');},
      writeManifest:async()=>{order3.push('manifest');},
      cleanup:async()=>{order3.push('cleanup');return {removed:[],warnings:[]};}
    }
  });
  assert.deepStrictEqual(order3,['manifest']);
  assert.strictEqual(metaApplied.mode,'MANIFEST_ONLY');


  // Cleanup removes only old manifest-tracked files and never recursively deletes legacy-untracked assets.
  class FakeEntryFile { constructor(){ this.kind='file'; } }
  class FakeEntryDir {
    constructor(entries={}) { this.kind='directory'; this.entriesMap=new Map(Object.entries(entries)); }
    async getDirectoryHandle(name){
      const v=this.entriesMap.get(name); if(!v || v.kind!=='directory'){const e=new Error('missing');e.name='NotFoundError';throw e;} return v;
    }
    async removeEntry(name, options){
      const v=this.entriesMap.get(name); if(!v){const e=new Error('missing');e.name='NotFoundError';throw e;}
      if(v.kind==='directory' && !(options&&options.recursive) && v.entriesMap.size>0){const e=new Error('Directory not empty');e.name='InvalidModificationError';throw e;}
      this.entriesMap.delete(name);
    }
  }
  const oldAssetsDir=new FakeEntryDir({
    'tracked.txt':new FakeEntryFile(),
    'legacy-untracked.bin':new FakeEntryFile()
  });
  const cleanupRoot=new FakeEntryDir({
    'Old_X.json':new FakeEntryFile(),
    'Old_X.md':new FakeEntryFile(),
    'Old_X_files':oldAssetsDir
  });
  const oldRecord={json_path:'Old_X.json',markdown_path:'Old_X.md',asset_dir:'Old_X_files',assets:[{path:'Old_X_files/tracked.txt'}]};
  const newRecord={json_path:'New_X.json',markdown_path:'New_X.md',asset_dir:null,assets:[]};
  const cleanupManifest={conversations:{X:newRecord}};
  const cleanupResult=await chCleanupTrackedOldPaths({rootHandle:cleanupRoot,oldRecord,newRecord,manifest:cleanupManifest,currentId:'X'});
  assert.strictEqual(cleanupRoot.entriesMap.has('Old_X.json'),false);
  assert.strictEqual(cleanupRoot.entriesMap.has('Old_X.md'),false);
  assert.strictEqual(oldAssetsDir.entriesMap.has('tracked.txt'),false);
  assert.strictEqual(oldAssetsDir.entriesMap.has('legacy-untracked.bin'),true);
  assert.strictEqual(cleanupRoot.entriesMap.has('Old_X_files'),true);

  // Full sync refuses an incomplete remote universe before any disk scan/write.
  await assert.rejects(
    ()=>chRunIntegratedDirectorySync({rootHandle:{},remoteList:[],selectedIds:null,remoteUniverseComplete:false}),
    /完整远端列表/
  );

  console.log('PASS final classification matrix');
  console.log('PASS canonical remote-universe merge');
  console.log('PASS attachment link relocation');
  console.log('PASS candidate-only detail fetch');
  console.log('PASS write -> manifest -> cleanup transaction ordering');
  console.log('PASS manifest-failure cleanup barrier');
  console.log('PASS in-place METADATA_ONLY manifest-only commit');
  console.log('PASS tracked-only cleanup preserves legacy-untracked assets');
  console.log('PASS incomplete full-sync stop condition');
})().catch(e=>{console.error(e);process.exit(1);});
