import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import vm from 'node:vm';
import {untilAborted} from '../../gui/managementCommand.js';
import {requestErrorMessage} from '../../gui/requestError.mjs';
import {restoreLostFocus} from '../../gui/restoreLostFocus.mjs';

const source=readFileSync(new URL('../../gui/OperationsJobs.jsx',import.meta.url),'utf8');
const start=source.indexOf('  async function inspectStatus('),end=source.indexOf('\n  function gpuTable(',start);
assert.ok(start>=0 && end>start);
test('예약·캡처 결과는 사라진 초점만 복구하고 사용자가 옮긴 초점은 유지한다',()=>{
  const begin=source.indexOf('  useEffect(()=>{if(busy || !auxFocus.current)'),end=source.indexOf('\n',begin);assert.ok(begin>=0 && end>begin);
  for(const [kind,recovery,moved,expected] of [['capture',null,false,'capture'],['inspection',null,false,'inspection'],['recovery',{},false,'recovery'],['recovery',null,false,'inspection'],['capture',null,true,null]]){
    const body={},other={},document={body,activeElement:moved?other:body},focused=[];
    const target=name=>({isConnected:true,disabled:false,focus(){focused.push(name);}});
    const context=vm.createContext({busy:false,inspection:'',capture:'',recovery,document,restoreLostFocus,auxFocus:{current:kind},inspectionResult:{current:target('inspection')},captureResult:{current:target('capture')},recoveryResult:{current:target('recovery')},useEffect:fn=>fn()});
    vm.runInContext(source.slice(begin,end),context);assert.deepEqual(focused,expected?[expected]:[]);assert.equal(context.auxFocus.current,null);
  }
});
test('운영 검토 취소는 원래 버튼이나 대기열 조회로 돌아가고 다른 초점은 유지한다',()=>{
  const begin=source.indexOf('  useEffect(()=>{if(busy || !cancelFocus.current)'),end=source.indexOf('\n',begin);
  const actionStart=source.indexOf('  function cancelOperation('),actionEnd=source.indexOf('\n',actionStart);assert.ok(begin>=0 && actionStart>=0);
  for(const [connected,moved,expected] of [[true,false,'origin'],[false,false,'reload'],[true,true,null]]){
    const body={},button={},other={},document={body,activeElement:button},focused=[];
    const origin={isConnected:connected,disabled:false,focus(){focused.push('origin');}},reload={isConnected:true,disabled:false,focus(){focused.push('reload');}};
    let cleared=false,effect;
    const context=vm.createContext({busy:false,priority:null,recovery:null,document,restoreLostFocus,cancelFocus:{current:null},gpuReload:{current:reload},useEffect:fn=>effect=fn});
    vm.runInContext(source.slice(actionStart,actionEnd)+'\n'+source.slice(begin,end)+'\nthis.cancelOperation=cancelOperation;',context);
    context.cancelOperation({currentTarget:button},{current:origin},()=>cleared=true);document.activeElement=moved?other:body;effect();
    assert.equal(cleared,true);assert.deepEqual(focused,expected?[expected]:[]);
  }
});
test('예약 신원·캡처 조회는 지연과 종료를 처리하고 재조회할 수 있다',async()=>{
  for(const [endpoint,label] of [['operations-reservation-inspect','예약 신원'],['operations-capture-status','캡처 접수 상태']])for(const stage of ['fetch','json','unmount']){
    let timer,finish,notice='',busy=false,calls=0,slow=true;const deferred=new Promise(resolve=>finish=resolve),priorityRequest={current:null};
    const context=vm.createContext({AbortController,untilAborted,requestErrorMessage,priorityPending:{current:false},priorityRequest,
      setTimeout:fn=>(timer=fn,1),clearTimeout:()=>{},setBusy:value=>busy=value,
      fetch:()=>{calls++;if(!slow)return Promise.resolve({ok:true,json:async()=>({notice:'조회 완료'})});return stage==='fetch'?deferred:Promise.resolve({ok:true,json:()=>deferred});}});
    vm.runInContext(source.slice(start,end)+'\nthis.inspectStatus=inspectStatus;',context);
    const pending=context.inspectStatus(endpoint,{},value=>notice=value,label);await context.inspectStatus(endpoint,{},value=>notice=value,label);assert.equal(calls,1);
    if(stage!=='fetch')await new Promise(resolve=>setImmediate(resolve));if(stage==='unmount')priorityRequest.current.abort();else timer();await pending;
    if(stage==='unmount')assert.equal(notice,'');else{assert.equal(busy,false);assert.match(notice,/시간이 초과/);}
    finish(stage==='fetch'?{ok:true,json:async()=>({notice:'늦음'})}:{notice:'늦음'});await new Promise(resolve=>setImmediate(resolve));assert.doesNotMatch(notice,/늦음/);
    if(stage!=='unmount'){slow=false;await context.inspectStatus(endpoint,{},value=>notice=value,label);assert.equal(notice,'조회 완료');}
  }
});
