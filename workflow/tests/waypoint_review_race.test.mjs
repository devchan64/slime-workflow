import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import vm from 'node:vm';
import {untilAborted} from '../../gui/managementCommand.js';

test('웨이포인트 검토 중 입력이 바뀌면 이전 검토 결과를 적용하지 않는다',async()=>{
 const source=readFileSync(new URL('../../gui/EffectEditor.jsx',import.meta.url),'utf8');
 const code=source.slice(source.indexOf('  async function review(){'),source.indexOf('  async function confirm(){'));
 let resolveRequest,pending=null,error='';const sourceRevision={current:0};
 const context=vm.createContext({AbortController,untilAborted,setTimeout,clearTimeout,sourceRevision,busy:false,previewRequest:{current:null},restoreFocus:{current:false},document:{activeElement:null},reviewButton:{current:null},
  source:'{"id":"a"}',detail:{document:{id:'a'},revision:'r'},setPending:value=>pending=value,setError:value=>error=value,setJsonError:()=>{},setBusy:()=>{},requestErrorMessage:problem=>problem.message,
  managementCommand:()=>new Promise(resolve=>resolveRequest=resolve),crypto:{randomUUID:()=> 'id'}});
 vm.runInContext(code,context);const request=context.review();sourceRevision.current++;
 resolveRequest({review_sha256:'a'.repeat(64),after:{id:'a',image:'i',animation:'a'},note:'n'});await request;
 assert.equal(pending,null);assert.match(error,/입력이 변경/);
});

test('웨이포인트 검토 시간 초과 직후 화면 종료 시 늦은 상태 변경을 막는다',async()=>{
 const source=readFileSync(new URL('../../gui/EffectEditor.jsx',import.meta.url),'utf8');
 const code=source.slice(source.indexOf('  async function review(){'),source.indexOf('  async function confirm(){'));
 let timeout,updates=0;const previewRequest={current:null};
 const context=vm.createContext({AbortController,untilAborted,sourceRevision:{current:0},busy:false,previewRequest,restoreFocus:{current:false},document:{activeElement:null},reviewButton:{current:null},
  source:'{"id":"a"}',detail:{document:{id:'a'},revision:'r'},setPending:()=>updates++,setError:()=>updates++,setJsonError:()=>updates++,setBusy:()=>updates++,requestErrorMessage:()=>'',
  setTimeout:fn=>{timeout=fn;return 1;},clearTimeout:()=>{},managementCommand:()=>new Promise(()=>{}),crypto:{randomUUID:()=> 'id'}});
 vm.runInContext(code,context);const request=context.review();timeout();const controller=previewRequest.current;previewRequest.current=null;controller.abort();const before=updates;
 await request;assert.equal(updates,before);
});

test('웨이포인트 검토 시간 초과 후 재시도하면 정상 결과를 표시한다',async()=>{
 const source=readFileSync(new URL('../../gui/EffectEditor.jsx',import.meta.url),'utf8');
 const code=source.slice(source.indexOf('  async function review(){'),source.indexOf('  async function confirm(){'));
 let timeout,fail=true,pending,error='',loading=false;const previewRequest={current:null};
 const context=vm.createContext({AbortController,untilAborted,sourceRevision:{current:0},busy:false,previewRequest,restoreFocus:{current:false},document:{activeElement:null},reviewButton:{current:null},
  source:'{"id":"a"}',detail:{document:{id:'a'},revision:'r'},setPending:value=>pending=value,setError:value=>error=value,setJsonError:()=>{},setBusy:value=>loading=value,requestErrorMessage:problem=>problem.message,
  setTimeout:fn=>{timeout=fn;return 1;},clearTimeout:()=>{},managementCommand:()=>fail ? new Promise(()=>{}) : Promise.resolve({review_sha256:'a'.repeat(64),after:{id:'a',image:'i',animation:'a'},note:'n'}),crypto:{randomUUID:()=> 'request-id'}});
 vm.runInContext(code,context);const first=context.review();timeout();await first;
 assert.match(error,/시간이 초과/);assert.equal(loading,false);assert.equal(previewRequest.current,null);
 fail=false;await context.review();
 assert.equal(error,'');assert.equal(loading,false);assert.equal(pending.requestId,'request-id');assert.equal(pending.draft.effect.id,'a');
});
