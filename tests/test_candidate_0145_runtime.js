const fs=require('fs');
const path=require('path');
const assert=require('assert');
const root=path.resolve(__dirname,'..');
const src=fs.readFileSync(path.join(root,'ChatHarbor.user.js'),'utf8');
const chT=(zh,en)=>zh;

const helperStart=src.indexOf('    const CH_ATTACHMENT_SOURCE_CATEGORIES');
const helperEnd=src.indexOf('    function chAttachmentReferenceKey',helperStart);
assert(helperStart>=0 && helperEnd>helperStart);
eval(src.slice(helperStart,helperEnd));

assert.strictEqual(chAttachmentSourceCategory('user','file',false),'user_upload');
assert.strictEqual(chAttachmentSourceCategory('assistant','sandbox',false),'assistant_generated_deliverable');
assert.strictEqual(chAttachmentSourceCategory('tool','file',true),'generated_media');
assert.strictEqual(chAttachmentSourceCategory('assistant','file',false),'assistant_asset');
assert.strictEqual(chAttachmentSourceCategory(null,'file',false),'unknown');
// Critical: file alone must not be treated as user upload.
assert.strictEqual(chAttachmentSourceCategory(null,'file',false),'unknown');

const stageStart=src.indexOf('    function chAttachmentFailureStage');
const stageEnd=src.indexOf('    function chAttachmentRunSummary',stageStart);
assert(stageStart>=0 && stageEnd>stageStart);
eval(src.slice(stageStart,stageEnd));
assert.strictEqual(chAttachmentFailureStage('metadata HTTP 404'),'metadata');
assert.strictEqual(chAttachmentFailureStage('download_url missing or expired'),'download_url');
assert.strictEqual(chAttachmentFailureStage('binary HTTP 415'),'binary');

const reportStart=src.indexOf('    function chAttachmentErrorInfo');
const reportEnd=src.indexOf('    function chPreflightReportText',reportStart);
assert(reportStart>=0 && reportEnd>reportStart);
eval(src.slice(reportStart,reportEnd));
assert.strictEqual(chAttachmentErrorInfo('metadata HTTP 404').short,'404');
assert.strictEqual(chAttachmentErrorInfo('metadata HTTP 403').short,'403');
assert.strictEqual(chAttachmentErrorInfo('binary HTTP 415').short,'415');
assert.strictEqual(chAttachmentErrorInfo('metadata HTTP 500').short,'500');
assert.strictEqual(chAttachmentErrorInfo('download_url missing or expired').short,'URL失效');

const summary={
  failedTotal:8,
  failedBySource:{user_upload:4,assistant_generated_deliverable:3,unknown:1},
  failedByKind:{file:5,sandbox:3},
  failedByStage:{metadata:4,download_url:2,binary:2},
  failedByError:{'metadata HTTP 404':3,'binary HTTP 415':2,'download_url missing or expired':2,'metadata HTTP 403':1},
  sourceByError:{
    user_upload:{'metadata HTTP 404':3,'metadata HTTP 403':1},
    assistant_generated_deliverable:{'binary HTTP 415':2,'download_url missing or expired':1},
    unknown:{'download_url missing or expired':1}
  },
  unknownFailures:1
};
const lines=chAttachmentProvenanceReportLines(summary).join('\n');
assert(lines.includes('历史未成功归档附件'));
assert(lines.includes('- 用户上传: 4'));
assert(lines.includes('- ChatGPT生成: 3'));
assert(lines.includes('3 × metadata HTTP 404'));
assert(lines.includes('2 × binary HTTP 415'));
assert(lines.includes('来源未知: 1'));
assert(lines.includes('Backfill/Migration Tool'));

console.log('PASS 0.0.14.5 runtime provenance classification, error explanations, historical breakdown');
