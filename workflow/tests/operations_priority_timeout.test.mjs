import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import vm from 'node:vm';
import {untilAborted} from '../../gui/managementCommand.js';
import {requestErrorMessage} from '../../gui/requestError.mjs';
import {restoreLostFocus} from '../../gui/restoreLostFocus.mjs';

const source=readFileSync(new URL('../../gui/OperationsJobs.jsx',import.meta.url),'utf8');
const start=source.indexOf('  async function readReceipt(event){'),end=source.indexOf('  const [inspection,',start);
assert.ok(start>=0 && end>start);
const methods=source.slice(start,end);

test('운영 우선 실행 결과는 잃은 초점만 적절한 결과나 오류로 복구한다',()=>{
  const begin=source.indexOf('  useEffect(()=>{if(busy || !priorityFocus.current)'),finish=source.indexOf('\n  async function readReceipt',begin);
  assert.ok(begin>=0 && finish>begin);
  for(const [kind,hasPriority,moved,expected] of [['receipt',false,false,'receipt'],['review',false,false,'error'],['review',true,false,'review'],['submit',true,false,'review'],['receipt',false,true,null]]){
    const body={},other={},focused=[],document={body,activeElement:moved?other:body};
    const target=name=>({isConnected:true,disabled:false,focus(){focused.push(name);}});
    const context=vm.createContext({busy:false,priority:hasPriority?{}:null,receiptNotice:'결과',gpuError:'오류',document,restoreLostFocus,priorityFocus:{current:kind},
      prioritySection:{current:target('review')},priorityError:{current:target('error')},receiptResult:{current:target('receipt')},useEffect:fn=>fn()});
    vm.runInContext(source.slice(begin,finish),context);assert.deepEqual(focused,expected?[expected]:[]);assert.equal(context.priorityFocus.current,null);
  }
});

test('운영 화면 접수·검토 조회는 요청과 본문 지연 시 대기를 해제한다',async()=>{
  for(const method of ['readReceipt','reviewPriority'])for(const stage of ['fetch','json']){
    let timeout,finish,busy=false,error='',calls=0;const deferred=new Promise(resolve=>finish=resolve);
    const context=vm.createContext({AbortController,untilAborted,requestErrorMessage,document:{activeElement:{}},priorityOrigin:{current:null},priorityFocus:{current:null},priorityPending:{current:false},priorityRequest:{current:null},receiptId:'priority_'+'a'.repeat(64),
      setTimeout:fn=>(timeout=fn,1),clearTimeout:()=>{},setBusy:value=>busy=value,setReceiptNotice:value=>error=value,setGpuError:value=>error=value,setPriority:()=>{},setReceiptId:()=>{},
      fetch:()=>{calls++;return stage==='fetch'?deferred:Promise.resolve({ok:true,json:()=>deferred});}});
    vm.runInContext(methods+'\nthis.action='+method+';',context);
    const pending=context.action('service','job');await context.action('service','job');assert.equal(calls,1);
    if(stage==='json')await new Promise(resolve=>setImmediate(resolve));timeout();await pending;
    assert.equal(busy,false);assert.match(error,/시간이 초과/);assert.equal(context.priorityPending.current,false);
    finish(stage==='fetch'?{ok:true,json:async()=>({notice:'늦음',identifier:''})}:{notice:'늦음',identifier:''});await new Promise(resolve=>setImmediate(resolve));assert.match(error,/시간이 초과/);
  }
});

test('운영 화면 우선 실행 응답이 늦으면 접수 ID를 유지하고 재전송하지 않는다',async()=>{
  let timeout,finish,busy=false,priority,calls=0;const request={request_id:'priority_'+'a'.repeat(64),service:'service',id:'job',ticket_revision:'b'.repeat(64)};
  const context=vm.createContext({AbortController,untilAborted,document:{activeElement:{}},priorityFocus:{current:null},priorityPending:{current:false},priorityRequest:{current:null},priority:{request},busy:false,
    setTimeout:fn=>(timeout=fn,1),clearTimeout:()=>{},setBusy:value=>busy=value,setPriority:value=>priority=value,
    managementCommand:()=>{calls++;return new Promise(resolve=>finish=resolve);}});
  vm.runInContext(methods+'\nthis.prioritize=prioritize;',context);
  const pending=context.prioritize();await context.prioritize();assert.equal(calls,1);assert.equal(priority.request,null);
  timeout();await pending;assert.equal(busy,false);assert.equal(priority.identifier,request.request_id);assert.match(priority.notice,/재접수하지 말고/);
  finish({state:'completed',request_id:request.request_id,service:request.service,job_id:request.id,ticket_revision:request.ticket_revision});await new Promise(resolve=>setImmediate(resolve));assert.match(priority.notice,/확인할 수 없습니다/);
});
test('운영 화면은 선택한 대상과 다른 검토 응답을 표시하지 않는다',async()=>{
  let priority='old',error='';const identifier='priority_'+'a'.repeat(64);
  const context=vm.createContext({AbortController,untilAborted,requestErrorMessage,document:{activeElement:{}},priorityOrigin:{current:null},priorityFocus:{current:null},priorityPending:{current:false},priorityRequest:{current:null},setTimeout,clearTimeout,
    setBusy:()=>{},setGpuError:value=>error=value,setPriority:value=>priority=value,setReceiptId:()=>{},setReceiptNotice:()=>{},
    fetch:async()=>({ok:true,json:async()=>({notice:'확인',identifier,request:{service:'other',id:'job',request_id:identifier,ticket_revision:'b'.repeat(64)}})})});
  vm.runInContext(methods+'\nthis.reviewPriority=reviewPriority;',context);await context.reviewPriority('service','job');
  assert.equal(priority,null);assert.match(error,/검토 대상을 확인할 수 없습니다/);
});
