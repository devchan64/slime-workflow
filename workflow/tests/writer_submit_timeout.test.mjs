import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import vm from 'node:vm';
import {untilAborted} from '../../gui/managementCommand.js';

const source=readFileSync(new URL('../../gui/WriterActions.jsx',import.meta.url),'utf8');
const code=source.slice(source.indexOf('  async function confirmHandoff(){'),source.indexOf('  const prepare='));
test('작가 직접 접수 시간 초과는 중복을 막고 접수 불확실 상태를 유지한다',async()=>{
 let timer,busy=false,uncertain=false,error='',calls=0,accepted=0;const storage=new Map();
 const context=vm.createContext({AbortController,untilAborted,setTimeout:fn=>(timer=fn,1),clearTimeout:()=>{},review:{confirmation:1,handoff:false,bound:{request:{mode:'write'}}},sending:{current:false},confirmation:{current:{claim:()=>true}},submitRequest:{current:null},mounted:{current:true},proposalScope:null,setBusy:value=>busy=value,setError:value=>error=value,sessionStorage:{setItem:(key,value)=>storage.set(key,value),removeItem:key=>storage.delete(key)},uncertaintyKey:'receipt',setUncertain:value=>uncertain=value,managementCommand:()=>{calls++;return new Promise(()=>{});},onAccepted:()=>accepted++,requestErrorMessage:error=>error.message,handoff:{clearReview:()=>{}},setReview:()=>{},reload:()=>{}});
 vm.runInContext(code+'\nthis.confirmHandoff=confirmHandoff;',context);const pending=context.confirmHandoff();await context.confirmHandoff();assert.equal(calls,1);timer();await pending;
 assert.equal(uncertain,true);assert.equal(storage.get('receipt'),'1');assert.match(error,/응답 시간이 초과/);assert.match(error,/실행 이력/);assert.equal(busy,false);assert.equal(accepted,0);
});
test('작가 제안 확인 중 화면을 닫으면 늦은 응답으로 접수하지 않는다',async()=>{
 for(const handoff of [false,true]){
  let resolve,dispatched=0,signal;const proposal={mode:'write',prompt:'내용'};
  const context=vm.createContext({AbortController,untilAborted,review:{confirmation:1,handoff,bound:{request:proposal}},sending:{current:false},confirmation:{current:{claim:()=>true}},submitRequest:{current:null},mounted:{current:true},proposalScope:{proposal,job:'job'},proposalId:'id',session:'s',setBusy:()=>{},setError:()=>{},setProposalReceipt:()=>{},readGenerationProposal:(_command,_scope,options)=>(signal=options.signal,new Promise(done=>resolve=done)),managementCommand:()=>{dispatched++;},handoff:{approve:async()=>dispatched++,clearReview:()=>{}},setReview:()=>{},reload:()=>{},requestErrorMessage:error=>error.message});
  vm.runInContext(code+'\nthis.confirmHandoff=confirmHandoff;',context);const pending=context.confirmHandoff();context.mounted.current=false;context.submitRequest.current.abort();resolve(proposal);await pending;
  assert.equal(signal.aborted,true);assert.equal(dispatched,0);
 }
});
