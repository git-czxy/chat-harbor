const fs=require('fs');
const assert=require('assert');
global.document={getElementById:()=>null,addEventListener:()=>{},hidden:false};
global.window={addEventListener:()=>{},fetch:async()=>({ok:true,status:200})};
global.localStorage={getItem:()=>null,setItem:()=>{}};
let fakeNow=0;
const realNow=Date.now;
Date.now=()=>fakeNow;
let sleepCalls=0;
const sleep=async(ms)=>{sleepCalls++; if(sleepCalls===1) fakeNow+=7200000; else fakeNow+=ms;};
function getConversation(){throw new Error('not used');}
function getExportButton(){return {};}
function setFabStatus(){}
function normalizeEpochSeconds(v){return Number(v)||0;}
function sanitizeFilename(x){return String(x||'');}
function generateUniqueFilename(c){return `${c?.conversation_id||'x'}.json`;}
function generateMarkdownFilename(c){return `${c?.conversation_id||'x'}.md`;}
function convertConversationToMarkdown(){return '';}
const layer=fs.readFileSync(require('path').join(__dirname,'integrated_sync_layer.js'),'utf8');
eval(layer);
(async()=>{
  assert.strictEqual(chFormatRemainingDuration(286000),'04:46');
  assert.strictEqual(chFormatRemainingDuration(1000),'00:01');
  assert.strictEqual(chFormatRemainingDuration(0),'00:00');
  const realRandom=Math.random; Math.random=()=>0;
  chBeginControlledRun({speedIndex:3,batchSize:20,batchPauseMinSec:180,batchPauseMaxSec:300,maxRetries:0});
  await chControlledSleep(210000,'保守批次暂停','测试210秒');
  // OS sleep exceeded the deadline, so the original 210 seconds are not replayed.
  // The selected safest preset adds an 18 second wake guard before the next request.
  assert(fakeNow>=7218000 && fakeNow<7219000,`unexpected fakeNow ${fakeNow}`);
  assert(sleepCalls<=25,`timer-tick replay detected: ${sleepCalls} sleeps`);
  chEndControlledRun();
  Math.random=realRandom; Date.now=realNow;
  console.log('PASS MM:SS batch-pause countdown formatter');
  console.log('PASS wall-clock deadline skips elapsed batch pause after system sleep');
  console.log('PASS wake guard jitter applied before next request');
})().catch(e=>{Date.now=realNow;console.error(e);process.exit(1);});
