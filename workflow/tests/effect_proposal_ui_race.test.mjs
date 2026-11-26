import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import vm from 'node:vm';
import {untilAborted} from '../../gui/managementCommand.js';
import {restoreLostFocus} from '../../gui/restoreLostFocus.mjs';
import {requestErrorMessage} from '../../gui/requestError.mjs';

test('저장 전 검증 중 화면을 종료하면 늦은 응답으로 저장을 접수하지 않는다',async()=>{
 const source=readFileSync(new URL('../../gui/EffectProposal.jsx',import.meta.url),'utf8');
 const code=source.slice(source.indexOf('  async function save()'),source.indexOf('  return <section',source.indexOf('  async function save()')));
 let resolve,dispatches=0,updates=0;const request={current:null},mounted={current:true};
 const context=vm.createContext({AbortController,request,mounted,sending:{current:false},review:{id:'r',draft:{id:'e'},preview:{token:'t'}},session:'s',job:'j',verifyEffectBeforeSave:()=>{},verifyProposalWithDeadline:()=>new Promise(done=>resolve=done),managementCommand:()=>dispatches++,setBusy:()=>updates++,setNotice:()=>updates++,setReceipt:()=>updates++,setReview:()=>updates++,requestErrorMessage:()=>''});
 vm.runInContext(code,context);const pending=context.save();mounted.current=false;const controller=request.current;request.current=null;controller.abort();const before=updates;resolve();await pending;assert.equal(dispatches,0);assert.equal(updates,before);
});

test('이펙트 제안 조회는 시간 초과 직후 화면 종료 시 상태를 변경하지 않는다',async()=>{
 const source=readFileSync(new URL('../../gui/EffectProposal.jsx',import.meta.url),'utf8');
 const code=source.slice(source.indexOf('  async function inspect()'),source.indexOf('  async function save()'));
 let timeout,updates=0;const request={current:null};
 const context=vm.createContext({AbortController,request,inspectFocus:{current:false},inspectRef:{current:null},document:{activeElement:null},session:'s',job:'j',snapshot:'h',offset:0,prepareEffectProposal:()=>{},setTimeout:fn=>(timeout=fn,1),clearTimeout:()=>{},
  setBusy:()=>updates++,setNotice:()=>updates++,setReview:()=>updates++,setReceipt:()=>updates++,readProposalPreview:(_prepare,_args,signal)=>untilAborted(new Promise(()=>{}),signal)});
 vm.runInContext(code,context);const pending=context.inspect();timeout();const controller=request.current;request.current=null;controller.abort();const before=updates;await pending;assert.equal(updates,before);
});

test('이펙트 제안 조회 연결 실패를 복구 가능한 안내로 표시한다',async()=>{
 const source=readFileSync(new URL('../../gui/EffectProposal.jsx',import.meta.url),'utf8');
 const code=source.slice(source.indexOf('  async function inspect()'),source.indexOf('  async function save()'));
 let notice='',busy=false;const context=vm.createContext({AbortController,request:{current:null},inspectFocus:{current:false},inspectRef:{current:null},document:{activeElement:null},session:'s',job:'j',snapshot:'h',offset:0,prepareEffectProposal:()=>{},setTimeout,clearTimeout,requestErrorMessage,
  setBusy:value=>busy=value,setNotice:value=>notice=value,setReview:()=>{},setReceipt:()=>{},readProposalPreview:async()=>{throw new TypeError('Failed to fetch');}});
 vm.runInContext(code,context);await context.inspect();assert.match(notice,/연결 상태를 확인/);assert.equal(busy,false);
});

test('이펙트 제안 취소는 검토 안에서 잃은 초점만 복구한다',()=>{
 const source=readFileSync(new URL('../../gui/EffectProposal.jsx',import.meta.url),'utf8');
 const start=source.indexOf('onCancel={()=>{const restore=reviewRef.current?.contains');const end=source.indexOf('}}/></div>',start);
 const code=source.slice(start+'onCancel={'.length,end+1);assert.ok(start>=0 && end>start);
 for(const scenario of ['lost','moved','outside']){
  let frame,focused=0;const body={},inside={},other={},document={body,activeElement:scenario==='outside'?other:inside};
  const context=vm.createContext({document,restoreLostFocus,reviewRef:{current:{contains:value=>value===inside}},inspectRef:{current:{isConnected:true,focus:()=>focused++}},focusFrame:{current:null},setReview:()=>{},cancelAnimationFrame:()=>{},requestAnimationFrame:fn=>(frame=fn,1)});
  vm.runInContext('('+code+')()',context);document.activeElement=scenario==='lost'?body:other;frame?.();assert.equal(focused,scenario==='lost'?1:0,scenario);
 }
});

test('이펙트 제안 검토가 열릴 때 잃은 초점만 옮기고 예약을 정리한다',()=>{
 const source=readFileSync(new URL('../../gui/EffectProposal.jsx',import.meta.url),'utf8');
 const effect=source.match(/useEffect\(\(\)=>\{if\(busy \|\| !inspectFocus\.current\).*?\},\[busy,review,receipt,notice\]\);/s)?.[0];assert.ok(effect);
 for(const kind of ['review','receipt','notice'])for(const moved of [false,true]){
  let run,frame,focused='',cancelled=0;const body={},other={},document={body,activeElement:moved?other:body};
  const target=name=>({current:{isConnected:true,focus:()=>focused=name}});
  const context=vm.createContext({document,restoreLostFocus,busy:false,review:kind==='review'?{}:null,receipt:kind==='receipt'?{}:null,notice:kind==='notice'?'오류':'',inspectFocus:{current:true},reviewRef:target('review'),receiptRef:target('receipt'),noticeRef:target('notice'),inspectRef:target('inspect'),useEffect:fn=>run=fn,requestAnimationFrame:fn=>(frame=fn,1),cancelAnimationFrame:()=>cancelled++});
  vm.runInContext(effect,context);const cleanup=run();frame();cleanup();assert.equal(focused,moved?'':kind);assert.equal(cancelled,1);
 }
});
