const fs = require('fs');
const path = require('path');
const assert = require('assert');
const { webcrypto } = require('crypto');
global.crypto = webcrypto;
global.document = { getElementById:()=>null, addEventListener:()=>{}, hidden:false };
global.window = { addEventListener:()=>{}, fetch: async()=>({ok:true,status:200}) };
global.localStorage = { getItem:()=>null, setItem:()=>{} };
const sleep = async()=>{};
const jitter = ()=>0;
function normalizeEpochSeconds(v){ return Number(v)||0; }
function sanitizeFilename(name){ return String(name||'').replace(/[\/\\?%*:|"<>]/g,'-').trim(); }
function encodeRelativePath(p){ return String(p).split('/').map(encodeURIComponent).join('/'); }
function generateUniqueFilename(c){ return `${sanitizeFilename(c.title||'Untitled')}_${(c.conversation_id||c.id||'id').split('-').pop()}.json`; }
function generateMarkdownFilename(c){ return generateUniqueFilename(c).replace(/\.json$/,'.md'); }
function chRemoteConversationId(e){ return String(e?.id||e?.conversation_id||''); }
function setFabStatus(){}
function getExportButton(){ return {}; }
async function ensureAccessToken(){ return true; }
async function getConversation(){ throw new Error('REMOTE_FETCH_MUST_NOT_RUN_DURING_LAYOUT_MIGRATION'); }
function collectVisibleAttachments(){ return []; }
async function fetchAttachmentBinary(){ throw new Error('REMOTE_ATTACHMENT_FETCH_MUST_NOT_RUN_DURING_LAYOUT_MIGRATION'); }
function convertConversationToMarkdown(){ return ''; }

function notFound(msg='not found'){ const e=new Error(msg); e.name='NotFoundError'; return e; }
function toBuffer(data){
  if (Buffer.isBuffer(data)) return Buffer.from(data);
  if (typeof data === 'string') return Buffer.from(data,'utf8');
  if (data instanceof ArrayBuffer) return Buffer.from(new Uint8Array(data));
  if (ArrayBuffer.isView(data)) return Buffer.from(data.buffer, data.byteOffset, data.byteLength);
  throw new Error('unsupported fake write');
}
class FakeFileHandle {
  constructor(name,data=Buffer.alloc(0)){ this.kind='file'; this.name=name; this.data=Buffer.from(data); }
  async getFile(){
    const data=Buffer.from(this.data);
    return {
      size:data.length,
      text:async()=>data.toString('utf8'),
      arrayBuffer:async()=>data.buffer.slice(data.byteOffset,data.byteOffset+data.byteLength)
    };
  }
  async createWritable(){
    const self=this; let staged=Buffer.alloc(0); let aborted=false;
    return {
      async write(data){ if(aborted) throw new Error('aborted'); staged=toBuffer(data); },
      async close(){ if(aborted) throw new Error('aborted'); self.data=Buffer.from(staged); },
      async abort(){ aborted=true; }
    };
  }
}
class FakeDirHandle {
  constructor(name='root'){ this.kind='directory'; this.name=name; this.entriesMap=new Map(); }
  async *entries(){ for(const kv of this.entriesMap) yield kv; }
  async getFileHandle(name,opts={}){
    const existing=this.entriesMap.get(name);
    if(existing){ if(existing.kind!=='file') throw new Error('type mismatch'); return existing; }
    if(!opts.create) throw notFound(name);
    const h=new FakeFileHandle(name); this.entriesMap.set(name,h); return h;
  }
  async getDirectoryHandle(name,opts={}){
    const existing=this.entriesMap.get(name);
    if(existing){ if(existing.kind!=='directory') throw new Error('type mismatch'); return existing; }
    if(!opts.create) throw notFound(name);
    const h=new FakeDirHandle(name); this.entriesMap.set(name,h); return h;
  }
  async removeEntry(name,opts={}){
    const existing=this.entriesMap.get(name);
    if(!existing) throw notFound(name);
    if(existing.kind==='directory' && !opts.recursive && existing.entriesMap.size){ const e=new Error('Directory not empty'); e.name='InvalidModificationError'; throw e; }
    this.entriesMap.delete(name);
  }
}
async function dirAt(root,dirPath,create=true){ let d=root; for(const seg of String(dirPath||'').split('/').filter(Boolean)) d=await d.getDirectoryHandle(seg,{create}); return d; }
async function putFile(root,filePath,data){ const parts=filePath.split('/').filter(Boolean); const name=parts.pop(); const d=await dirAt(root,parts.join('/'),true); const h=await d.getFileHandle(name,{create:true}); h.data=toBuffer(data); }
async function getBytes(root,filePath){ const parts=filePath.split('/').filter(Boolean); const name=parts.pop(); const d=await dirAt(root,parts.join('/'),false); const f=await (await d.getFileHandle(name)).getFile(); return Buffer.from(new Uint8Array(await f.arrayBuffer())); }
async function exists(root,p){ try{ await getBytes(root,p); return true; }catch(e){ if(e.name==='NotFoundError') return false; throw e; } }
async function readJson(root,p){ return JSON.parse((await getBytes(root,p)).toString('utf8')); }

const layer=fs.readFileSync(path.join(__dirname,'integrated_sync_layer.js'),'utf8');
eval(layer);

(async()=>{
  const root=new FakeDirHandle('chatgpt');
  const rootJson=JSON.stringify({conversation_id:'ROOT-ID',title:'Root Chat',mapping:{a:{}},current_node:'a'});
  const rootMd='# User\nhello\n\n![pic](Root%20Chat_ROOT-ID_files/pic.png)\n';
  const projectJson=JSON.stringify({conversation_id:'PROJ-ID',title:'Project Chat',mapping:{b:{}},current_node:'b'});
  const projectMd='# User\nproject\n';
  await putFile(root,'Root Chat_ROOT-ID.json',rootJson);
  await putFile(root,'Root Chat_ROOT-ID.md',rootMd);
  await putFile(root,'Root Chat_ROOT-ID_files/pic.png',Buffer.from([1,2,3,4]));
  await putFile(root,'Root Chat_ROOT-ID_files/legacy.bin',Buffer.from([9,9,9]));
  await putFile(root,'My Project/Project Chat_PROJ-ID.json',projectJson);
  await putFile(root,'My Project/Project Chat_PROJ-ID.md',projectMd);

  const manifest={
    schema_version:1, product:'ChatHarbor', source:'ChatGPT', identity:'conversation_id', signature_version:'sha256-current_node+mapping-v1',
    created_at:'2026-09-14T00:00:00.000Z', updated_at:'2026-09-14T00:00:00.000Z', conversations:{
      'ROOT-ID':{
        conversation_id:'ROOT-ID',title:'Root Chat',remote_update_time:100,is_archived:false,project_id:null,project_title:null,
        json_path:'Root Chat_ROOT-ID.json',markdown_path:'Root Chat_ROOT-ID.md',asset_dir:'Root Chat_ROOT-ID_files',
        assets:[{path:'Root Chat_ROOT-ID_files/pic.png',markdown_path:'Root%20Chat_ROOT-ID_files/pic.png',name:'pic.png',kind:'file',size_bytes:4}],
        content_signature:'sig-root',signature_version:'sha256-current_node+mapping-v1'
      },
      'PROJ-ID':{
        conversation_id:'PROJ-ID',title:'Project Chat',remote_update_time:100,is_archived:false,project_id:'p1',project_title:'My Project',
        json_path:'My Project/Project Chat_PROJ-ID.json',markdown_path:'My Project/Project Chat_PROJ-ID.md',asset_dir:null,assets:[],
        content_signature:'sig-proj',signature_version:'sha256-current_node+mapping-v1'
      }
    }
  };
  await putFile(root,'ChatHarbor_manifest.json',JSON.stringify(manifest,null,2));

  const before=await chArchiveLayoutState(root);
  assert.strictEqual(before.layoutVersion,1);
  assert.strictEqual(before.requiresMigration,true);
  assert.strictEqual(before.total,2);
  assert.strictEqual(before.project,1);
  assert.strictEqual(before.root,1);

  const progress=[];
  const result=await chMigrateArchiveLayoutV1ToV2(root,x=>progress.push(x));
  assert.strictEqual(result.migrated,2);
  assert.strictEqual(result.archiveLayoutVersion,2);
  assert(progress.length>=2);

  const afterManifest=await readJson(root,'ChatHarbor_manifest.json');
  assert.strictEqual(afterManifest.provider,'chatgpt');
  assert.strictEqual(afterManifest.archive_layout_version,2);
  assert.strictEqual(afterManifest.migration_state,undefined);
  assert.strictEqual(afterManifest.conversations['ROOT-ID'].json_path,'conversations/Root Chat_ROOT-ID.json');
  assert.strictEqual(afterManifest.conversations['ROOT-ID'].markdown_path,'conversations/Root Chat_ROOT-ID.md');
  assert.strictEqual(afterManifest.conversations['ROOT-ID'].asset_dir,'conversations/Root Chat_ROOT-ID_files');
  assert.strictEqual(afterManifest.conversations['ROOT-ID'].assets[0].path,'conversations/Root Chat_ROOT-ID_files/pic.png');
  assert.strictEqual(afterManifest.conversations['PROJ-ID'].json_path,'projects/My Project/Project Chat_PROJ-ID.json');
  assert.strictEqual(afterManifest.conversations['PROJ-ID'].markdown_path,'projects/My Project/Project Chat_PROJ-ID.md');

  assert.strictEqual((await getBytes(root,'conversations/Root Chat_ROOT-ID.json')).toString(),rootJson);
  assert.strictEqual((await getBytes(root,'conversations/Root Chat_ROOT-ID.md')).toString(),rootMd);
  assert.deepStrictEqual([...await getBytes(root,'conversations/Root Chat_ROOT-ID_files/pic.png')],[1,2,3,4]);
  assert.strictEqual((await getBytes(root,'projects/My Project/Project Chat_PROJ-ID.json')).toString(),projectJson);
  assert.strictEqual((await getBytes(root,'projects/My Project/Project Chat_PROJ-ID.md')).toString(),projectMd);

  assert.strictEqual(await exists(root,'Root Chat_ROOT-ID.json'),false);
  assert.strictEqual(await exists(root,'Root Chat_ROOT-ID.md'),false);
  assert.strictEqual(await exists(root,'Root Chat_ROOT-ID_files/pic.png'),false);
  // Untracked legacy material is deliberately preserved and therefore keeps the old asset directory alive.
  assert.strictEqual(await exists(root,'Root Chat_ROOT-ID_files/legacy.bin'),true);
  assert.strictEqual(await exists(root,'My Project/Project Chat_PROJ-ID.json'),false);
  assert.strictEqual(root.entriesMap.has('My Project'),false);

  const after=await chArchiveLayoutState(root);
  assert.strictEqual(after.layoutVersion,2);
  assert.strictEqual(after.requiresMigration,false);

  // Migrated records remain eligible for fast UNCHANGED classification; layout movement alone
  // must not create UPDATE/RENAME work or require detail fetch.
  const migratedManifest=await readJson(root,'ChatHarbor_manifest.json');
  const migratedRecords=new Map(Object.entries(migratedManifest.conversations).map(([id,r])=>[id,{...r,tracking:'manifest'}]));
  const migratedScan={
    recordsById:migratedRecords, duplicateIds:new Set(), duplicates:[], blockedIds:new Set(), errors:[], errorsById:new Map(),
    stats:{manifestTracked:2,manifestProject:1,manifestRoot:1,archiveLayoutVersion:2,provider:'chatgpt',migrationRequired:false,rawConversationFiles:2,rawOnlyIds:0}
  };
  const matchingRemote=[
    {id:'ROOT-ID',title:'Root Chat',update_time:migratedManifest.conversations['ROOT-ID'].remote_update_time,is_archived:false,projectId:null,projectTitle:null},
    {id:'PROJ-ID',title:'Project Chat',update_time:migratedManifest.conversations['PROJ-ID'].remote_update_time,is_archived:false,projectId:'p1',projectTitle:'My Project'}
  ];
  const postMigrationPlan=chBuildPreflightPlan(matchingRemote,migratedScan);
  assert.strictEqual(postMigrationPlan.summary.unchangedCount,2);
  assert.strictEqual(postMigrationPlan.summary.maximumFetchRequired,0);

  const rerun=await chMigrateArchiveLayoutV1ToV2(root);
  assert.strictEqual(rerun.alreadyCurrent,true);

  // Resume case: v2 files are already committed in manifest, but old tracked source remains.
  const resume=new FakeDirHandle('chatgpt');
  await putFile(resume,'Old.json','old-json');
  await putFile(resume,'Old.md','old-md');
  await putFile(resume,'conversations/Old.json','old-json');
  await putFile(resume,'conversations/Old.md','old-md');
  const resumeManifest={
    schema_version:1,product:'ChatHarbor',source:'ChatGPT',provider:'chatgpt',identity:'conversation_id',signature_version:'sha256-current_node+mapping-v1',
    created_at:'x',updated_at:'x',migration_state:{type:'archive_layout',from:1,to:2,status:'in_progress',started_at:'x'},
    conversations:{R:{conversation_id:'R',title:'Old',project_id:null,project_title:null,json_path:'conversations/Old.json',markdown_path:'conversations/Old.md',asset_dir:null,assets:[],content_signature:'s',signature_version:'sha256-current_node+mapping-v1',migration_previous_paths:{json_path:'Old.json',markdown_path:'Old.md',asset_dir:null,assets:[]}}}
  };
  await putFile(resume,'ChatHarbor_manifest.json',JSON.stringify(resumeManifest,null,2));
  const resumed=await chMigrateArchiveLayoutV1ToV2(resume);
  assert.strictEqual(resumed.migrated,1);
  assert.strictEqual(await exists(resume,'Old.json'),false);
  assert.strictEqual(await exists(resume,'Old.md'),false);
  const resumeAfter=await readJson(resume,'ChatHarbor_manifest.json');
  assert.strictEqual(resumeAfter.archive_layout_version,2);
  assert.strictEqual(resumeAfter.conversations.R.migration_previous_paths,undefined);

  console.log('PASS Layout v1 -> v2 local-only migration');
  console.log('PASS v2 conversations/projects namespace paths');
  console.log('PASS byte-identical JSON/Markdown/assets after migration');
  console.log('PASS untracked legacy asset preservation');
  console.log('PASS resumable migration after manifest commit / before cleanup');
  console.log('PASS migrated conversations remain fast-path UNCHANGED when remote metadata matches');
  console.log('PASS migration idempotence (v2 rerun is no-op)');
})().catch(err=>{ console.error(err); process.exit(1); });
