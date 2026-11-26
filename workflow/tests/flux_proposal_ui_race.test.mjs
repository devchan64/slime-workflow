import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import vm from 'node:vm';
import {untilAborted} from '../../gui/managementCommand.js';
import {requestErrorMessage} from '../../gui/requestError.mjs';

test('이미지 제안 조회가 시간 초과되면 재시도할 수 있고 종료 후 갱신하지 않는다',async()=>{
 const source=readFileSync(new URL('../../gui/FluxProposal.jsx',import.meta.url),'utf8');
 const code=source.slice(source.indexOf('  async function load(event)'),source.indexOf('  async function prepare(event)'));
 for(const unmount of [false,true]){
  let timeout,busy=false,error='',updates=0;const loadRequest={current:null},button={};
  const context=vm.createContext({AbortController,loadRequest,busy:false,session:'s',job:'j',snapshot:'h',offset:0,pendingFocus:{current:false},document:{activeElement:button},verifyFluxProposal:()=>{},requestErrorMessage,setTimeout:fn=>(timeout=fn,1),clearTimeout:()=>{},setBusy:value=>{busy=value;updates++;},setError:value=>{error=value;updates++;},setProposal:()=>updates++,readProposalPreview:(_fn,_args,signal)=>untilAborted(new Promise(()=>{}),signal)});
  vm.runInContext(code,context);const pending=context.load({currentTarget:button});timeout();if(unmount){loadRequest.current=null;}const before=updates;await pending;
  if(unmount)assert.equal(updates,before);else{assert.equal(busy,false);assert.match(error,/시간이 초과/);assert.equal(loadRequest.current,null);}
 }
});

test('이미지 접수폼 자동 조회가 복구돼도 직접 검토 오류는 유지한다',async()=>{
 const source=readFileSync(new URL('../../gui/FluxProposal.jsx',import.meta.url),'utf8');
 const start=source.indexOf('    async function refresh()');const end=source.indexOf('    refresh();',start);const code=source.slice(start,end);assert.ok(start>=0&&end>start);
 let calls=0,pollError='',manualError='직접 검토 오류';const context=vm.createContext({active:true,timer:null,attempts:0,controller:new AbortController(),session:'s',job:'j',snapshot:'h',offset:0,requestErrorMessage,managementCommand:async()=>{if(++calls===1)throw new TypeError('Failed to fetch');return {forms:[]};},setPollError:value=>pollError=value,setError:value=>manualError=value,setPrepared:()=>{},setProposal:()=>{},setTimeout:()=>1});
 vm.runInContext(code,context);await context.refresh();assert.match(pollError,/연결 상태를 확인/);await context.refresh();assert.equal(pollError,'');assert.equal(manualError,'직접 검토 오류');
});
