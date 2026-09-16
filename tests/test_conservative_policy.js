const fs = require('fs');
const assert = require('assert');
global.document={getElementById:()=>null};
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
const layer=fs.readFileSync('/mnt/data/chatharbor_stage4/integrated_sync_layer.js','utf8');
eval(layer);

(async()=>{
  const d=chNormalizeNetworkPolicy({});
  assert.deepStrictEqual(d,{speedIndex:3,batchSize:20,batchPauseMinSec:180,batchPauseMaxSec:300,maxRetries:2});
  assert.deepStrictEqual(chNormalizeNetworkPolicy({speedIndex:99,batchSize:0,batchPauseMinSec:400,batchPauseMaxSec:10,maxRetries:99}),
    {speedIndex:5,batchSize:1,batchPauseMinSec:400,batchPauseMaxSec:400,maxRetries:5});
  const random0=Math.random; Math.random=()=>0; assert.strictEqual(chNetworkDelayMs({speedIndex:3}),6000); Math.random=()=>1; assert.strictEqual(chNetworkDelayMs({speedIndex:3}),10000); Math.random=random0;
  assert.strictEqual(chRetryDelayMs(new Error('HTTP 429'),1),120000);
  assert.strictEqual(chRetryDelayMs(new Error('failed (503)'),2),60000);
  assert.strictEqual(chRetryDelayMs(new Error('failed (401)'),1),null);

  const run=chBeginControlledRun({speedIndex:3,batchSize:20,batchPauseMinSec:180,batchPauseMaxSec:300,maxRetries:2});
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

  const patcher=fs.readFileSync('/mnt/data/chatharbor_integrated_sync_070/ChatHarbor_IntegratedSync_patch.py','utf8');
  for (const marker of ['ch-pause-sync-btn','ch-cancel-sync-btn','同步仍在运行','controlsDisabled = state.loading || chSyncRun.active','batchPauseMinSec: 180','batchPauseMaxSec: 300']) {
    assert(patcher.includes(marker),`missing static marker: ${marker}`);
  }
  console.log('PASS conservative defaults 6-10s / 20 / 180-300s');
  console.log('PASS policy normalization and retry delays');
  console.log('PASS pause/resume checkpoint');
  console.log('PASS graceful cancel checkpoint');
  console.log('PASS back-navigation/runtime control guards present');
})().catch(e=>{console.error(e);process.exit(1);});
