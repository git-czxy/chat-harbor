const fs = require('fs');
const assert = require('assert');
const { webcrypto } = require('crypto');
global.crypto = webcrypto;
global.document={getElementById:()=>null,addEventListener:()=>{},hidden:false};
global.window={addEventListener:()=>{}};
global.localStorage={getItem:()=>null,setItem:()=>{}};
const CH_SIGNATURE_VERSION = 'sha256-current_node+mapping-v1';

function normalizeEpochSeconds(value) {
  if (!value) return 0;
  if (typeof value === 'number' && Number.isFinite(value)) return value > 1e12 ? Math.floor(value / 1000) : value;
  if (typeof value === 'string') { const p=Date.parse(value); return Number.isNaN(p)?0:Math.floor(p/1000); }
  return 0;
}
function sanitizeFilename(name){ return String(name||'').replace(/[\/\\?%*:|"<>]/g,'-').trim(); }
function encodeRelativePath(path){ return String(path||'').split('/').map(encodeURIComponent).join('/'); }
function uniqueAttachmentName(filename,used){ let name=String(filename||'attachment'); if(!used.has(name)){used.add(name);return name;} let i=2; while(used.has(`${name}_${i}`)) i++; const out=`${name}_${i}`; used.add(out); return out; }
function generateUniqueFilename(c){ return `${sanitizeFilename(c.title||'Untitled')}_${(c.conversation_id||c.id||'id').split('-').pop()}.json`; }
function generateMarkdownFilename(c){ return generateUniqueFilename(c).replace(/\.json$/,'.md'); }
function chRemoteConversationId(e){ return String(e?.id||e?.conversation_id||''); }
function chTimeEquivalent(a,b){ const aa=normalizeEpochSeconds(a),bb=normalizeEpochSeconds(b); return !!aa&&!!bb&&Math.abs(aa-bb)<=0.001; }
function chGetConversationId(entry, convData){ return convData?.conversation_id||convData?.id||entry?.id||null; }
function collectVisibleAttachments(){ return []; }
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

const layer=fs.readFileSync(require('path').join(__dirname,'integrated_sync_layer.js'),'utf8');
eval(layer);
chContentSignature = async (c)=> c.__sig || 'sig';
chShowIntegratedSyncReport = ()=>{};

(async()=>{
  // Remote-universe merge must collapse discovery duplicates by canonical ID.
  const merged=chMergeRemoteEntries([
    {id:'A',title:'A',update_time:10},
    {id:'A',title:'A',update_time:10,projectId:'p',projectTitle:'P'},
    {id:'B',title:'B',update_time:9}
  ]);
  assert.strictEqual(merged.length,2);
  assert.strictEqual(merged.find(x=>x.id==='A').projectTitle,'P');
  const conflict=chMergeRemoteEntries([
    {id:'Z',title:'Z',update_time:10,is_archived:true,__chArchiveState:'known'},
    {id:'Z',title:'Z',update_time:10,is_archived:false,__chArchiveState:'known'}
  ])[0];
  assert.strictEqual(conflict.__chArchiveState,'unknown');
  const projectConflict=chMergeRemoteEntries([
    {id:'PZ',title:'PZ',update_time:10,projectId:'p1',projectTitle:'P1',__chProjectState:'known'},
    {id:'PZ',title:'PZ',update_time:10,projectId:'p2',projectTitle:'P2',__chProjectState:'known'}
  ])[0];
  assert.strictEqual(projectConflict.__chProjectState,'unknown');
  assert.strictEqual(projectConflict.projectId,null);
  const headA=[{id:'A',title:'A',update_time:10,__chSourceKey:'root:active',__chArchiveState:'known',is_archived:false,__chProjectState:'unknown'}];
  const headB=[...headA].reverse();
  assert.strictEqual(chHeadFingerprint(headA),chHeadFingerprint(headB));
  assert.notStrictEqual(chHeadFingerprint(headA),chHeadFingerprint([{...headA[0],update_time:11}]));

  const manifestLocal=(title='T',sig='same',time=100,extra={})=>({
    conversation_id:'X', title, content_signature:sig, remote_update_time:time, tracking:'manifest',
    is_archived:false, project_id:null, project_title:null, json_path:'conversations/T_X.json', markdown_path:'conversations/T_X.md', assets:[], ...extra
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
  assert.strictEqual(r.finalAction,'OBSERVATION_ONLY');

  r=await chClassifyFetchedConversation(baseItem(manifestLocal('T','same',100),{id:'X',title:'T',update_time:100,is_archived:true,projectId:null,projectTitle:null}),{conversation_id:'X',title:'T',update_time:100,__sig:'same'});
  assert.strictEqual(r.finalAction,'METADATA_ONLY');

  r=await chClassifyFetchedConversation(baseItem(manifestLocal('T','same',100)),{conversation_id:'X',title:'T',update_time:100,__sig:'same'});
  assert.strictEqual(r.finalAction,'OBSERVATION_ONLY');

  r=await chClassifyFetchedConversation(baseItem(manifestLocal('T','',100)),{conversation_id:'X',title:'T',update_time:101,__sig:'same'});
  assert.strictEqual(r.finalAction,'ERROR');
  assert(r.finalReasons.includes('LOCAL_SIGNATURE_MISSING'));

  r=await chClassifyFetchedConversation(baseItem({...manifestLocal(),tracking:'raw_only',content_signature:undefined}),{conversation_id:'X',title:'T',update_time:100,__sig:'same'});
  assert.strictEqual(r.finalAction,'LOCAL_UNTRACKED');
  assert.strictEqual(r.contentChanged,null);

  // Attachment links remain valid when Markdown relocates across project directories.
  assert.strictEqual(
    chRelativeMarkdownPath('projects/New Project/','projects/Old Project/T_files/a b.pdf'),
    '../Old%20Project/T_files/a%20b.pdf'
  );
  assert.strictEqual(
    chRelativeMarkdownPath('conversations/','projects/Old Project/T_files/a b.pdf'),
    '../projects/Old%20Project/T_files/a%20b.pdf'
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
  const localM={...manifestLocal('T','same',100),json_path:'conversations/T_X.json',markdown_path:'conversations/T_X.md'};
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

  // A successful verification with unchanged content must advance the remote-list checkpoint.
  const oldObserved={...manifestLocal('T','same',100),synced_at:'2026-01-01T00:00:00.000Z'};
  const manifestObs={conversations:{X:oldObserved}};
  const observationItem={id:'X',finalAction:'OBSERVATION_ONLY',remote:{id:'X',title:'T',update_time:101,is_archived:false,projectId:null,projectTitle:null,__chProjectState:'none',__chArchiveState:'known'},convData:{conversation_id:'X',title:'T',update_time:100,__sig:'same'},newSignature:'same',attachmentInspection:{state:'none',detected:0,missing:0}};
  const obsApplied=await chApplyClassifiedSyncItem({rootHandle:{},classifiedItem:observationItem,manifest:manifestObs,deps:{writeConversation:async()=>{throw new Error('must not write');},writeManifest:async()=>{},cleanup:async()=>({removed:[],warnings:[]})}});
  assert.strictEqual(obsApplied.mode,'MANIFEST_ONLY');
  assert.strictEqual(manifestObs.conversations.X.remote_list_update_time,101);
  assert.strictEqual(manifestObs.conversations.X.synced_at,'2026-01-01T00:00:00.000Z');
  const scanObs={recordsById:new Map([['X',{...manifestObs.conversations.X,tracking:'manifest'}]]),duplicateIds:new Set(),duplicates:[],blockedIds:new Set(),errors:[],errorsById:new Map(),stats:{manifestTracked:1,manifestProject:0,manifestRoot:1,archiveLayoutVersion:2,provider:'chatgpt',migrationRequired:false,rawConversationFiles:0,rawOnlyIds:0,trackedFastChecked:1}};
  const converged=chBuildPreflightPlan([{id:'X',title:'T',update_time:101,is_archived:false,projectId:null,projectTitle:null,__chProjectState:'none',__chArchiveState:'known'}],scanObs);
  assert.strictEqual(converged.items[0].action,'UNCHANGED');
  assert.strictEqual(converged.summary.maximumFetchRequired,0);

  // Attachment policy is independent: default-off does not trigger verification; turning it on does.
  const unknownAttachment={...manifestObs.conversations.X,attachment_state:'unknown',remote_list_update_time:101,remote_list_title:'T',remote_list_is_archived:false,remote_list_project_id:null,remote_list_project_title:null,tracking:'manifest'};
  const attachScan={...scanObs,recordsById:new Map([['X',unknownAttachment]])};
  assert.strictEqual(chBuildPreflightPlan([{id:'X',title:'T',update_time:101,is_archived:false,projectId:null,projectTitle:null,__chProjectState:'none',__chArchiveState:'known'}],attachScan,null,{includeAttachments:false}).items[0].action,'UNCHANGED');
  const attachPlan=chBuildPreflightPlan([{id:'X',title:'T',update_time:101,is_archived:false,projectId:null,projectTitle:null,__chProjectState:'none',__chArchiveState:'known'}],attachScan,null,{includeAttachments:true});
  assert.strictEqual(attachPlan.items[0].action,'VERIFY_CHANGED');
  assert(attachPlan.items[0].reasons.includes('ATTACHMENT_UNKNOWN'));

  // Legacy attachment evidence may safely converge without another detail request when it
  // proves that a positive detected set was completely downloaded.  Zero remains UNKNOWN.
  const legacyAsset={kind:'file',source_file_id:'file-a',path:'conversations/T_X_files/a.pdf',name:'a.pdf',size_bytes:10};
  const legacyComplete={...unknownAttachment};
  delete legacyComplete.attachment_state;
  Object.assign(legacyComplete,{attachment_detected:1,attachment_downloaded:1,attachment_failed:0,assets:[legacyAsset]});
  assert.strictEqual(chRecordAttachmentState(legacyComplete),'complete');
  const legacyCompletePlan=chBuildPreflightPlan([{id:'X',title:'T',update_time:101,is_archived:false,projectId:null,projectTitle:null,__chProjectState:'none',__chArchiveState:'known'}],{...scanObs,recordsById:new Map([['X',legacyComplete]])},null,{includeAttachments:true});
  assert.strictEqual(legacyCompletePlan.items[0].action,'UNCHANGED');

  const legacyPartial={...legacyComplete,attachment_detected:2,attachment_downloaded:1,attachment_failed:1};
  assert.strictEqual(chRecordAttachmentState(legacyPartial),'partial');
  const legacyZero={...legacyComplete,attachment_detected:0,attachment_downloaded:0,attachment_failed:0,assets:[]};
  delete legacyZero.attachments_checked_at;
  assert.strictEqual(chRecordAttachmentState(legacyZero),'unknown');

  // Missing-only attachment backfill reuses already tracked current-reference assets, fetches
  // only the missing references, and emits a monotonic completion counter.
  const originalCollect=collectVisibleAttachments;
  collectVisibleAttachments=()=>[
    {kind:'file',fileId:'file-a',messageId:'m1',ownerRole:'user',name:'a.pdf',isImage:false},
    {kind:'file',fileId:'file-b',messageId:'m2',ownerRole:'user',name:'b.pdf',isImage:false},
    {kind:'file',fileId:'file-c',messageId:'m3',ownerRole:'user',name:'c.pdf',isImage:false}
  ];
  const existingBackfill={asset_dir:'conversations/T_X_files',assets:[
    {kind:'file',source_file_id:'file-a',path:'conversations/T_X_files/a.pdf',markdown_path:'T_X_files/a.pdf',name:'a.pdf',message_id:'m1',owner_role:'user',size_bytes:10},
    {kind:'file',source_file_id:'file-c',path:'conversations/T_X_files/c.pdf',markdown_path:'T_X_files/c.pdf',name:'c.pdf',message_id:'m3',owner_role:'user',size_bytes:10}
  ]};
  const planBackfill=chPlanAttachmentBackfill({conversation_id:'X'},existingBackfill);
  assert.strictEqual(planBackfill.retained.length,2);
  assert.strictEqual(planBackfill.missing.length,1);
  assert.strictEqual(planBackfill.missing[0].fileId,'file-b');
  const fetchedAssets=[]; const progressCounts=[];
  const resultBackfill=await chWriteAttachmentsToDirectory(
    {getDirectoryHandle:async()=>({})},
    {conversation_id:'X',title:'T'},
    null,
    (p)=>progressCounts.push(p.assetIndex),
    {
      targetPrefix:'conversations/',
      existingRecord:existingBackfill,
      fetchAttachmentBinary:async(ref)=>{fetchedAssets.push(ref.fileId);return {filename:`${ref.fileId}.pdf`,data:new Uint8Array([1,2,3])};},
      writeAttachment:async()=>{}
    }
  );
  collectVisibleAttachments=originalCollect;
  assert.deepStrictEqual(fetchedAssets,['file-b']);
  assert.strictEqual(resultBackfill.files.length,3);
  assert.strictEqual(resultBackfill.reusedCount,2);
  assert.strictEqual(resultBackfill.downloadedNow,1);
  assert.strictEqual(resultBackfill.attemptedNow,1);
  assert.deepStrictEqual(progressCounts,[2,3]);
  assert(progressCounts.every((value,index)=>index===0 || value>=progressCounts[index-1]));


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

  // Streaming sync must classify and commit each fetched conversation before fetching the next one.
  const streamOrder=[];
  chScanLocalArchiveReadOnly = async()=>({manifestExists:false,manifestReadable:true});
  chBuildPreflightPlan = ()=>({
    items:[
      {id:'S1',action:'NEW',needs_detail_fetch:true,remote:{id:'S1',title:'S1',update_time:1},local:null},
      {id:'S2',action:'NEW',needs_detail_fetch:true,remote:{id:'S2',title:'S2',update_time:1},local:null}
    ],
    summary:{scopeRemote:2,maximumFetchRequired:2,localOnlyReliable:true,localOnlyCount:0}
  });
  chReadManifest = async()=>({schema_version:1,identity:'conversation_id',conversations:{}});
  getConversation = async(id)=>{streamOrder.push(`fetch:${id}`);return {conversation_id:id,title:id,update_time:1,__sig:`sig-${id}`};};
  chApplyClassifiedSyncItem = async({classifiedItem})=>{streamOrder.push(`commit:${classifiedItem.id}`);return {mode:'FILES_AND_MANIFEST',record:{},cleanup:{warnings:[]}};};
  const streamResult=await chRunIntegratedDirectorySync({
    rootHandle:{},remoteList:[{id:'S1'},{id:'S2'}],selectedIds:new Set(['S1','S2']),remoteUniverseComplete:true,
    networkPolicy:{speedIndex:0,batchSize:1,batchPauseMinSec:0,batchPauseMaxSec:0,maxRetries:0}
  });
  assert.deepStrictEqual(streamOrder,['fetch:S1','commit:S1','fetch:S2','commit:S2']);
  assert.strictEqual(streamResult.sync.succeeded,2);
  assert.strictEqual(streamResult.verification.detailFetchCount,2);
  chEndControlledRun();

  // Preflight-confirmed fast-path items must be accounted for immediately and omitted from the runtime work queue.
  const skipOrder=[];
  chBuildPreflightPlan = ()=>({
    items:[
      {id:'U1',action:'UNCHANGED',needs_detail_fetch:false,remote:{id:'U1',title:'U1',update_time:1},local:{}},
      {id:'N1',action:'NEW',needs_detail_fetch:true,remote:{id:'N1',title:'N1',update_time:2},local:null}
    ],
    summary:{scopeRemote:2,maximumFetchRequired:1,localOnlyReliable:true,localOnlyCount:0}
  });
  getConversation = async(id)=>{skipOrder.push(`fetch:${id}`);return {conversation_id:id,title:id,update_time:2,__sig:`sig-${id}`};};
  chApplyClassifiedSyncItem = async({classifiedItem,conversationIndex,conversationTotal})=>{skipOrder.push(`commit:${classifiedItem.id}:${conversationIndex+1}/${conversationTotal}`);return {mode:'FILES_AND_MANIFEST',record:{},cleanup:{warnings:[]}};};
  const skipResult=await chRunIntegratedDirectorySync({
    rootHandle:{},remoteList:[{id:'U1'},{id:'N1'}],selectedIds:new Set(['U1','N1']),remoteUniverseComplete:true,
    networkPolicy:{speedIndex:0,batchSize:1,batchPauseMinSec:0,batchPauseMaxSec:0,maxRetries:0}
  });
  assert.deepStrictEqual(skipOrder,['fetch:N1','commit:N1:1/1']);
  assert.strictEqual(skipResult.verification.counts.UNCHANGED,1);
  assert.strictEqual(skipResult.verification.detailFetchCount,1);
  chEndControlledRun();

  console.log('PASS final classification matrix');
  console.log('PASS canonical remote-universe merge + ambiguity preservation');
  console.log('PASS remote-head stable fingerprint / change detection');
  console.log('PASS attachment link relocation');
  console.log('PASS candidate-only detail fetch');
  console.log('PASS write -> manifest -> cleanup transaction ordering');
  console.log('PASS manifest-failure cleanup barrier');
  console.log('PASS in-place METADATA_ONLY / OBSERVATION_ONLY manifest-only commit');
  console.log('PASS repeated-verification convergence checkpoint');
  console.log('PASS attachment completeness policy separation');
  console.log('PASS tracked-only cleanup preserves legacy-untracked assets');
  console.log('PASS incomplete full-sync stop condition');
  console.log('PASS streaming fetch -> classify -> atomic commit ordering');
  console.log('PASS preflight-confirmed items skip the runtime work queue');
})().catch(e=>{console.error(e);process.exit(1);});
