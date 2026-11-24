import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import vm from 'node:vm';
import {untilAborted} from '../../gui/managementCommand.js';

const source=readFileSync(new URL('../../gui/QueuePriority.jsx',import.meta.url),'utf8');
test('기존 우선 실행 접수는 검토 대신 같은 기록의 확인 상태로 연결한다',async()=>{
  const start=source.indexOf('  async function preview() {'),end=source.indexOf('\n  async function submit()',start);
  assert.ok(start>=0 && end>start);
  for(const state of ['unknown','completed','not_found']){
    let notice='',uncertain=null,review=null;const revision='a'.repeat(64),request_id='priority_'+'00'.repeat(32),calls=[];
    const context=vm.createContext({AbortController,untilAborted,TextEncoder,Uint8Array,crypto:{subtle:{digest:async()=>new Uint8Array(32).buffer}},
      service:'service',id:'job',verifyTarget:async()=>{},previewRequest:{current:null},setTimeout,clearTimeout,
      setNotice:value=>notice=value,setUncertain:value=>uncertain=value,setReview:value=>review=value,
      call:async(command)=>{calls.push(command);return command==='priority-preview'?{service:'service',job_id:'job',ticket_revision:revision,queue_position:1,queue_count:2}:state==='not_found'?{state}:{state,request_id,service:'service',job_id:'job',ticket_revision:revision};}});
    vm.runInContext(source.slice(start,end)+'\nthis.preview=preview;',context);await context.preview();
    if(state==='not_found'){assert.ok(review);assert.equal(uncertain,null);}else{assert.equal(review,null);assert.equal(uncertain.request_id,request_id);assert.match(notice,state==='completed'?/접수 완료/:/재접수하지 마세요/);}
    assert.deepEqual(calls,['priority-preview','priority-receipt']);
  }
});
test('우선 실행 검토와 확인은 렌더 전에도 중복 실행되지 않고 실패 뒤 재시도할 수 있다',async()=>{
  const start=source.indexOf('  async function run(action) {'),end=source.indexOf('\n  if(inline)',start);
  assert.ok(start>=0 && end>start);
  let finish,calls=0,busy=false,notice='';
  const context=vm.createContext({mounted:{current:true},interactionPending:{current:false},setBusy:value=>busy=value,setNotice:value=>notice=value});
  vm.runInContext(source.slice(start,end)+'\nthis.run=run;',context);
  const action=()=>{calls++;return new Promise((resolve,reject)=>finish={resolve,reject});};
  const first=context.run(action);await context.run(action);
  assert.equal(calls,1);assert.equal(busy,true);
  finish.reject(new Error('조회 실패'));await first;
  assert.equal(notice,'조회 실패');assert.equal(busy,false);
  const next=context.run(action);assert.equal(calls,2);finish.resolve();await next;
  assert.equal(busy,false);assert.equal(context.interactionPending.current,false);
});
test('접수 기록 조회 지연과 화면 종료 뒤에는 늦은 응답을 적용하지 않는다',async()=>{
  const start=source.indexOf('  async function checkReceipt(){'),end=source.indexOf('\n  async function run(',start);
  for(const stop of ['timeout','unmount']){
    let timeout,finish,notice='';const mounted={current:true},previewRequest={current:null},uncertain={request_id:'priority_test',ticket_revision:'v'};
    const context=vm.createContext({AbortController,untilAborted,uncertain,service:'service',id:'job',mounted,previewRequest,
      setTimeout:fn=>(timeout=fn,1),clearTimeout:()=>{},setNotice:value=>notice=value,call:()=>new Promise(resolve=>finish=resolve)});
    vm.runInContext(source.slice(start,end)+'\nthis.checkReceipt=checkReceipt;',context);
    const pending=context.checkReceipt();if(stop==='timeout')timeout();else{mounted.current=false;previewRequest.current.abort();}
    await pending;if(stop==='timeout')assert.match(notice,/확인하지 못했습니다/);else assert.equal(notice,'');
    finish({state:'completed',request_id:uncertain.request_id,ticket_revision:'v',service:'service',job_id:'job'});
    await new Promise(resolve=>setImmediate(resolve));assert.doesNotMatch(notice,/접수 완료/);
    assert.equal(previewRequest.current,null);
  }
});
test('우선 실행 응답 지연은 불확실 상태로 잠그고 늦은 응답을 적용하지 않는다',async()=>{
  const start=source.indexOf('  async function submit() {'),end=source.indexOf('\n  async function run(',start);
  assert.ok(start>=0 && end>start);
  let timeout,finish,notice='',uncertain=false,reviewCleared=false,calls=0;
  const payload={request_id:'priority_test',ticket_revision:'v'},button={};
  const context=vm.createContext({AbortController,untilAborted,verifyPriorityTarget:async()=>{},verifyTarget:null,
    review:{payload},service:'service',id:'job',previewRequest:{current:null},mounted:{current:true},restoreFocus:{current:true},
    reviewRef:{current:{contains:element=>element===button}},document:{activeElement:button},
    setReview:value=>reviewCleared=value===null,setNotice:value=>notice=value,setUncertain:value=>uncertain=value,
    setTimeout:fn=>(timeout=fn,1),clearTimeout:()=>{},call:()=>{calls++;return new Promise(resolve=>finish=resolve);}});
  vm.runInContext(source.slice(start,end)+'\nthis.submit=submit;',context);
  const pending=context.submit();await new Promise(resolve=>setImmediate(resolve));assert.equal(calls,1);assert.equal(reviewCleared,true);
  timeout();await pending;assert.equal(uncertain,payload);assert.match(notice,/접수 기록과 대기열/);assert.equal(context.restoreFocus.current,true);
  finish({state:'completed',service:'service',job_id:'job',...payload});await Promise.resolve();assert.match(notice,/확인할 수 없습니다/);
  assert.match(source,/disabled=\{disabled \|\| busy \|\| uncertain \|\| Boolean\(review\)\}/);
  assert.match(source,/disabled=\{busy \|\| uncertain\}/);
});
test('우선 실행 확인 전 초점을 기억하고 조회 실패나 접수 불확실 시 잃은 초점만 복구한다',()=>{
  const begin=source.indexOf('  useEffect(()=>{if(!busy && restoreFocus.current)'),end=source.indexOf('\n  async function preview()',begin);
  assert.ok(begin>=0 && end>begin);
  for(const outcome of ['review','uncertain','moved']){
    const body={},button={},other={},focused=[],document={body,activeElement:button};
    const target=name=>({focus(){focused.push(name);}});
    const context=vm.createContext({document,busy:false,review:outcome==='review'?{}:null,uncertain:outcome==='uncertain',
      triggerRef:{current:target('trigger')},reviewRef:{current:{...target('review'),contains:element=>element===button}},noticeRef:{current:target('notice')},
      restoreFocus:{current:false},interactionPending:{current:false},useEffect:fn=>{context.effect=fn;},run:()=>{},preview:()=>{},submit:()=>{},setReview:()=>{}});
    vm.runInContext(source.slice(begin,end)+'\nthis.startSubmit=startSubmit;',context);
    context.startSubmit();assert.equal(context.restoreFocus.current,true);
    document.activeElement=outcome==='moved'?other:body;context.effect();
    assert.deepEqual(focused,outcome==='moved'?[]:[outcome==='review'?'review':'notice']);
  }
});
test('불확실한 접수는 같은 ID를 읽기 전용으로 확인하고 불일치와 미기록을 완료로 표시하지 않는다',async()=>{
  const start=source.indexOf('  async function checkReceipt(){'),end=source.indexOf('\n  async function run(',start);
  assert.ok(start>=0 && end>start);
  const uncertain={request_id:'priority_test',ticket_revision:'revision'};let response,notice='',calls=[];
  const context=vm.createContext({AbortController,untilAborted,uncertain,service:'service',id:'job',mounted:{current:true},previewRequest:{current:null},setTimeout,clearTimeout,setNotice:value=>notice=value,call:(command,payload)=>{calls.push([command,payload.request_id]);return Promise.resolve(response);}});
  vm.runInContext(source.slice(start,end)+'\nthis.checkReceipt=checkReceipt;',context);
  response={state:'not_found'};await context.checkReceipt();assert.match(notice,/아직 접수 기록이 없습니다/);
  response={state:'completed',request_id:uncertain.request_id,service:'other',job_id:'job',ticket_revision:uncertain.ticket_revision};await context.checkReceipt();assert.match(notice,/확인하지 못했습니다/);
  response={...response,service:'service'};await context.checkReceipt();assert.match(notice,/순서 변경 접수 완료/);
  assert.deepEqual(calls,[['priority-receipt','priority_test'],['priority-receipt','priority_test'],['priority-receipt','priority_test']]);
});
