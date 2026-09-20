const fs = require('fs');
const assert = require('assert');
global.document={getElementById:()=>null,addEventListener:()=>{},hidden:false};
global.window={addEventListener:()=>{},fetch:async()=>({ok:true,status:200})};
global.localStorage={getItem:()=>null,setItem:()=>{}};
const sleep=ms=>new Promise(r=>setTimeout(r, Math.min(ms, 1)));
function normalizeEpochSeconds(v){return Number(v)||0;}
function getConversation(){ throw new Error('not stubbed'); }
function getExportButton(){return {};}
function setFabStatus(){}
function collectVisibleAttachments(){return [];}
function encodeRelativePath(x){return x;}
function generateUniqueFilename(c){return `${c.title||'T'}_${c.conversation_id||c.id||'X'}.json`;}
function generateMarkdownFilename(c){return generateUniqueFilename(c).replace(/\.json$/,'.md');}
function convertConversationToMarkdown(){return '';}
function sanitizeFilename(x){return x;}
const layer=fs.readFileSync(require('path').join(__dirname,'integrated_sync_layer.js'),'utf8');
eval(layer);

(async()=>{
  const d=chNormalizeNetworkPolicy({});
  assert.deepStrictEqual(d,{speedIndex:2,batchSize:10,batchPauseMinSec:120,batchPauseMaxSec:180,maxRetries:2});
  assert.deepStrictEqual(chNormalizeNetworkPolicy({speedIndex:99,batchSize:0,batchPauseMinSec:400,batchPauseMaxSec:10,maxRetries:99}),
    {speedIndex:3,batchSize:1,batchPauseMinSec:400,batchPauseMaxSec:400,maxRetries:5});
  const random0=Math.random; Math.random=()=>0; assert.strictEqual(chNetworkDelayMs({speedIndex:2}),12000); Math.random=()=>1; assert.strictEqual(chNetworkDelayMs({speedIndex:2}),18000); Math.random=random0;
  assert.strictEqual(chRetryDelayMs(new Error('HTTP 429'),1),300000);
  assert.strictEqual(chRetryDelayMs(new Error('failed (503)'),2),60000);
  assert.strictEqual(chRetryDelayMs(new Error('failed (401)'),1),null);

  const run=chBeginControlledRun({speedIndex:2,batchSize:10,batchPauseMinSec:120,batchPauseMaxSec:180,maxRetries:2});
  assert.strictEqual(run.active,true);
  chRequestPause();
  let resumed=false;
  const wait=chControlCheckpoint('test-pause').then(()=>{resumed=true;});
  setTimeout(()=>chResumeRun(),2);
  await wait;
  assert.strictEqual(resumed,true);

  assert.strictEqual(chRequestCancel('test'),true);
  await assert.rejects(()=>chControlCheckpoint('test-cancel'), e=>e && e.code==='CHATHARBOR_CANCELLED');
  chEndControlledRun();

  const runtime=fs.readFileSync(require('path').join(__dirname,'..','ChatHarbor.user.js'),'utf8');
  for (const marker of ['ch-pause-sync-btn','ch-cancel-sync-btn','同步仍在运行','batchSize: 10','batchPauseMinSec: 120','batchPauseMaxSec: 180','chatharbor_network_policy_v2','大量任务（更稳）']) {
    assert(runtime.includes(marker),`missing static marker: ${marker}`);
  }
  console.log('PASS safer default preset 12-18s / 10 / 120-180s');
  console.log('PASS policy normalization and retry delays');
  console.log('PASS pause/resume checkpoint');
  console.log('PASS graceful cancel checkpoint');
  console.log('PASS back-navigation/runtime control guards present');
})().catch(e=>{console.error(e);process.exit(1);});
