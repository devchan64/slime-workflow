import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import vm from 'node:vm';
import {untilAborted} from '../../gui/managementCommand.js';

const source=readFileSync(new URL('../../gui/WriterActions.jsx',import.meta.url),'utf8');
const code=source.slice(source.indexOf('  async function submit(mode) {'),source.indexOf('  async function confirmHandoff(){'));
function fixture(command){
 let timeout,busy=false,error,review,reloads=0,calls=0;
 const context=vm.createContext({AbortController,untilAborted,setTimeout:fn=>(timeout=fn,1),clearTimeout:()=>{},statePending:{current:false},sending:{current:false},uncertain:false,proposalScope:null,reviewRequest:{current:null},reviewEpoch:{current:0},reviewFocusFrame:{current:null},reviewTrigger:{current:null},document:{activeElement:{}},setBusy:value=>busy=value,setError:value=>error=value,session:'session',prompt:'내용',workspace:{},managementCommand:(...args)=>{calls++;return command(...args);},handoff:{preview:async()=>false},confirmation:{current:{open:()=>1}},setReview:value=>review=value,reload:()=>reloads++,requestErrorMessage:error=>error.message});
 vm.runInContext(code+'\nthis.submit=submit;',context);return {context,timeout:()=>timeout(),busy:()=>busy,error:()=>error,review:()=>review,reloads:()=>reloads,calls:()=>calls};
}
test('준비 상태 조회 중에는 빠른 작업 검토 요청을 보내지 않는다',async()=>{
 const f=fixture(()=>assert.fail('준비 상태 조회 중에는 요청하지 않음'));f.context.statePending.current=true;
 await f.context.submit('write');assert.equal(f.calls(),0);assert.equal(f.busy(),false);
});
test('작가 검토 조회 지연은 중복을 막고 시간 초과 뒤 다시 시도할 수 있다',async()=>{
 const f=fixture(()=>new Promise(()=>{})),pending=f.context.submit('write');await f.context.submit('write');assert.equal(f.calls(),1);f.timeout();await pending;
 assert.match(f.error(),/시간이 초과/);assert.equal(f.busy(),false);assert.equal(f.review(),undefined);assert.equal(f.context.sending.current,false);assert.equal(f.reloads(),1);
});
test('작가 화면 종료 후 늦은 작업공간 응답은 검토를 열지 않는다',async()=>{
 let resolve;const f=fixture(()=>new Promise(done=>resolve=done)),pending=f.context.submit('write'),controller=f.context.reviewRequest.current;
 f.context.reviewRequest.current=null;controller.abort();resolve({session_id:'session',fingerprint:'a'.repeat(64),document_root:'a',state_root:'b'});await pending;
 assert.equal(f.review(),undefined);assert.equal(f.reloads(),0);assert.equal(f.error(),'');
});
test('작가 검토 취소의 초점 복구는 새 검토와 사용자 이동을 방해하지 않는다',()=>{
 const cancel=source.slice(source.indexOf('  function cancelReview(){'),source.indexOf('  async function confirmHandoff(){'));
 for(const mode of ['lost','moved','new']){
  const body={},inside={},other={};let frame,focused=0;
  const context=vm.createContext({document:{body,activeElement:inside},reviewRef:{current:{contains:value=>value===inside}},reviewTrigger:{current:{isConnected:true,disabled:false,matches:()=>false,focus:()=>focused++}},reviewEpoch:{current:1},reviewRequest:{current:null},reviewFocusFrame:{current:null},confirmation:{current:{cancel:()=>{}}},setReview:()=>{},handoff:{clearReview:()=>{}},requestAnimationFrame:fn=>(frame=fn,1),cancelAnimationFrame:()=>{},restoreLostFocus:(doc,target)=>{if(doc.activeElement===doc.body && target.isConnected && !target.disabled)target.focus();}});
  vm.runInContext(cancel+'\nthis.cancelReview=cancelReview;',context);context.cancelReview();context.document.activeElement=mode==='moved'?other:body;if(mode==='new')context.reviewEpoch.current++;frame();assert.equal(focused,mode==='lost'?1:0);
 }
});
