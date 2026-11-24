import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import vm from 'node:vm';
import {untilAborted} from '../../gui/managementCommand.js';
import {validKeyframeBatchResult} from '../../gui/keyframeBatchValidation.mjs';

test('키프레임 검증 중 배치가 바뀌면 이전 검증 결과를 적용하지 않는다',async()=>{
 const source=readFileSync(new URL('../../gui/KeyframeCatalog.jsx',import.meta.url),'utf8');
 const code=source.slice(source.indexOf('  async function validate(event)'),source.indexOf('  return <>',source.indexOf('  async function validate(event)')));
 let resolveRequest,review=null,error='';const inputRevision={current:0};
 const context=vm.createContext({AbortController,untilAborted,setTimeout,clearTimeout,inputRevision,validationRequest:{current:null},duplicateFrames:new Set(),restoreValidationFocus:{current:false},document:{activeElement:null},validateButton:{current:null},
  rows:[{id:'a',frame:1}],frames:30,setBusy:()=>{},setError:value=>error=value,setReview:value=>review=value,requestErrorMessage:problem=>problem.message,validKeyframeBatchResult:()=>true,
  managementCommand:()=>new Promise(resolve=>resolveRequest=resolve)});
 vm.runInContext(code,context);const request=context.validate({preventDefault(){}});inputRevision.current++;
 resolveRequest({placements:[]});await request;
 assert.equal(review,null);assert.match(error,/배치가 변경/);
});

test('키프레임 검증 시간 초과 직후 화면을 닫으면 늦은 상태 변경을 막는다',async()=>{
 const source=readFileSync(new URL('../../gui/KeyframeCatalog.jsx',import.meta.url),'utf8');
 const code=source.slice(source.indexOf('  async function validate(event)'),source.indexOf('  return <>',source.indexOf('  async function validate(event)')));
 let timeout,updates=0;const validationRequest={current:null};
 const context=vm.createContext({AbortController,untilAborted,inputRevision:{current:0},validationRequest,duplicateFrames:new Set(),restoreValidationFocus:{current:false},document:{activeElement:null},validateButton:{current:null},
  rows:[{id:'a',frame:1}],frames:30,setBusy:()=>updates++,setError:()=>updates++,setReview:()=>updates++,requestErrorMessage:()=>'',validKeyframeBatchResult:()=>true,
  setTimeout:fn=>{timeout=fn;return 1;},clearTimeout:()=>{},managementCommand:()=>new Promise(()=>{})});
 vm.runInContext(code,context);const request=context.validate({preventDefault(){}});timeout();const controller=validationRequest.current;validationRequest.current=null;controller.abort();const before=updates;
 await request;assert.equal(updates,before);
});

test('키프레임 검증 시간 초과 후 재시도하면 정상 배치를 표시한다',async()=>{
 const source=readFileSync(new URL('../../gui/KeyframeCatalog.jsx',import.meta.url),'utf8');
 const code=source.slice(source.indexOf('  async function validate(event)'),source.indexOf('  return <>',source.indexOf('  async function validate(event)')));
 let timeout,fail=true,review=null,error='',loading=false;const validationRequest={current:null},id='a'.repeat(32),hash='b'.repeat(64);
 const context=vm.createContext({AbortController,untilAborted,inputRevision:{current:0},validationRequest,duplicateFrames:new Set(),restoreValidationFocus:{current:false},document:{activeElement:null},validateButton:{current:null},
  rows:[{id,frame:1}],frames:30,setBusy:value=>loading=value,setError:value=>error=value,setReview:value=>review=value,requestErrorMessage:problem=>problem.message,validKeyframeBatchResult,
  setTimeout:fn=>{timeout=fn;return 1;},clearTimeout:()=>{},managementCommand:()=>fail ? new Promise(()=>{}) : Promise.resolve({placements:[{id,frame:1}],note:'확인',skeleton_signature_sha256:hash,sources:[{id,preview_sha256:hash,source_sha256:hash}]})});
 vm.runInContext(code,context);const first=context.validate({preventDefault(){}});timeout();await first;
 assert.match(error,/시간이 초과/);assert.equal(loading,false);assert.equal(validationRequest.current,null);
 fail=false;await context.validate({preventDefault(){}});
 assert.equal(error,'');assert.equal(loading,false);assert.equal(review.placements[0].id,id);
});
