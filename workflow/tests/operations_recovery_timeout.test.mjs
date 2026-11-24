import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import vm from 'node:vm';
import {untilAborted} from '../../gui/managementCommand.js';
import {requestErrorMessage} from '../../gui/requestError.mjs';

const source=readFileSync(new URL('../../gui/OperationsJobs.jsx',import.meta.url),'utf8');
const start=source.indexOf('  async function reviewRecovery(target,event){'),end=source.indexOf('\n  async function inspectReservation',start);
assert.ok(start>=0 && end>start);
const methods=source.slice(start,end);
test('예약 정리 검토는 요청과 본문 지연 때 중복을 막고 대기를 해제한다',async()=>{
  for(const stage of ['fetch','json']){
    let timer,finish,busy=false,inspection='',calls=0;const delayed=new Promise(resolve=>finish=resolve);
    const context=vm.createContext({AbortController,untilAborted,requestErrorMessage,rememberAuxFocus:()=>{},recoveryOrigin:{current:null},priorityPending:{current:false},priorityRequest:{current:null},
      setTimeout:fn=>(timer=fn,1),clearTimeout:()=>{},setBusy:value=>busy=value,setInspection:value=>inspection=value,setRecovery:()=>{},setOutsideChecked:()=>{},setReceiptNotice:()=>{},setReceiptId:()=>{},
      fetch:()=>{calls++;return stage==='fetch'?delayed:Promise.resolve({ok:true,json:()=>delayed});}});
    vm.runInContext(methods+'\nthis.reviewRecovery=reviewRecovery;',context);
    const pending=context.reviewRecovery({service:'s',job_id:'j'});await context.reviewRecovery({service:'s',job_id:'j'});assert.equal(calls,1);
    if(stage==='json')await new Promise(resolve=>setImmediate(resolve));timer();await pending;
    assert.equal(busy,false);assert.match(inspection,/시간이 초과/);
    finish(stage==='fetch'?{ok:true,json:async()=>({})}:{});await new Promise(resolve=>setImmediate(resolve));assert.match(inspection,/시간이 초과/);
  }
});
test('예약 정리 응답 지연은 접수 ID를 유지하고 재실행하지 않는다',async()=>{
  let timer,finish,busy=false,inspection='',receiptId='',recovery,calls=0;
  const request={request_id:'recovery_'+'a'.repeat(64),service:'s',job_id:'j',review_sha256:'b'.repeat(64)};
  const context=vm.createContext({AbortController,untilAborted,rememberAuxFocus:()=>{},priorityPending:{current:false},priorityRequest:{current:null},busy:false,outsideChecked:true,recovery:{request},
    setTimeout:fn=>(timer=fn,1),clearTimeout:()=>{},setBusy:value=>busy=value,setRecovery:value=>recovery=value,setOutsideChecked:()=>{},setInspection:value=>inspection=value,setReceiptId:value=>receiptId=value,
    managementCommand:()=>{calls++;return new Promise(resolve=>finish=resolve);}});
  vm.runInContext(methods+'\nthis.recover=recover;',context);const pending=context.recover();await context.recover();assert.equal(calls,1);assert.equal(recovery,null);
  timer();await pending;assert.equal(busy,false);assert.equal(receiptId,request.request_id);assert.match(inspection,/재실행하지 말고/);
  finish({state:'completed',request_id:request.request_id,service:'s',job_id:'j'});await new Promise(resolve=>setImmediate(resolve));assert.match(inspection,/확인할 수 없습니다/);
});
test('예약 정리 검토는 선택한 예약과 다른 응답을 거부한다',async()=>{
  let recovery,inspection='';const identifier='recovery_'+'a'.repeat(64);
  const context=vm.createContext({AbortController,untilAborted,requestErrorMessage,rememberAuxFocus:()=>{},recoveryOrigin:{current:null},priorityPending:{current:false},priorityRequest:{current:null},setTimeout,clearTimeout,
    setBusy:()=>{},setInspection:value=>inspection=value,setRecovery:value=>recovery=value,setOutsideChecked:()=>{},setReceiptNotice:()=>{},setReceiptId:()=>{},
    fetch:async()=>({ok:true,json:async()=>({notice:'검토',identifier,request:{request_id:identifier,service:'other',job_id:'j',review_sha256:'b'.repeat(64)}})})});
  vm.runInContext(methods+'\nthis.reviewRecovery=reviewRecovery;',context);await context.reviewRecovery({service:'s',job_id:'j'});
  assert.equal(recovery,null);assert.match(inspection,/검토 대상을 확인할 수 없습니다/);
});
