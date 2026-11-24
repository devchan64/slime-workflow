import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import vm from 'node:vm';
import {requestErrorMessage} from '../../gui/requestError.mjs';
import {restoreLostFocus} from '../../gui/restoreLostFocus.mjs';

test('빌보드 저장 전 검증 중 종료하면 늦은 응답으로 저장하지 않는다',async()=>{
 const source=readFileSync(new URL('../../gui/BillboardProposal.jsx',import.meta.url),'utf8');
 const code=source.slice(source.indexOf('  async function save()'),source.indexOf('  return <section',source.indexOf('  async function save()')));
 let resolve,dispatches=0,updates=0;const request={current:null},mounted={current:true};
 const context=vm.createContext({AbortController,request,mounted,sending:{current:false},review:{id:'r',draft:{changes:[]},preview:{token:'t',review_sha256:'h'}},session:'s',job:'j',verifyBillboardBeforeSave:()=>{},verifyProposalWithDeadline:()=>new Promise(done=>resolve=done),managementCommand:()=>dispatches++,validateBillboardReceipt:()=>{},setBusy:()=>updates++,setError:()=>updates++,setReceipt:()=>updates++,setReview:()=>updates++,requestErrorMessage});
 vm.runInContext(code,context);const pending=context.save();mounted.current=false;const controller=request.current;request.current=null;controller.abort();const before=updates;resolve();await pending;assert.equal(dispatches,0);assert.equal(updates,before);
});

test('빌보드 제안 조회 후 잃은 초점만 검토·접수·오류로 옮긴다',()=>{
 const source=readFileSync(new URL('../../gui/BillboardProposal.jsx',import.meta.url),'utf8');
 const effect=source.match(/useEffect\(\(\)=>\{if\(busy \|\| !inspectFocus\.current\).*?\},\[busy,review,receipt,error\]\);/s)?.[0];assert.ok(effect);
 for(const kind of ['review','receipt','error'])for(const moved of [false,true]){
  let run,frame,focused='';const body={},other={},document={body,activeElement:moved?other:body},target=name=>({current:{isConnected:true,focus:()=>focused=name}});
  const context=vm.createContext({document,restoreLostFocus,busy:false,review:kind==='review'?{}:null,receipt:kind==='receipt'?{}:null,error:kind==='error'?'오류':'',inspectFocus:{current:true},reviewRef:target('review'),receiptRef:target('receipt'),errorRef:target('error'),inspectRef:target('inspect'),useEffect:fn=>run=fn,requestAnimationFrame:fn=>(frame=fn,1),cancelAnimationFrame:()=>{}});
  vm.runInContext(effect,context);const cleanup=run();frame();cleanup();assert.equal(focused,moved?'':kind);
 }
});

test('빌보드 검토 취소는 검토 영역에서 잃은 초점만 복구한다',()=>{
 const source=readFileSync(new URL('../../gui/BillboardProposal.jsx',import.meta.url),'utf8');
 const start=source.indexOf('onCancel={()=>{const restore=reviewRef.current?.contains'),end=source.indexOf('}}/></div>',start);assert.ok(start>=0 && end>start);
 const code=source.slice(start+'onCancel={'.length,end+1);
 for(const scenario of ['lost','moved','outside']){
  let frame,focused=0;const body={},inside={},other={},document={body,activeElement:scenario==='outside'?other:inside};
  const context=vm.createContext({document,restoreLostFocus,reviewRef:{current:{contains:value=>value===inside}},inspectRef:{current:{isConnected:true,focus:()=>focused++}},focusFrame:{current:null},setReview:()=>{},cancelAnimationFrame:()=>{},requestAnimationFrame:fn=>(frame=fn,1)});
  vm.runInContext('('+code+')()',context);document.activeElement=scenario==='lost'?body:other;frame?.();assert.equal(focused,scenario==='lost'?1:0,scenario);
 }
});
