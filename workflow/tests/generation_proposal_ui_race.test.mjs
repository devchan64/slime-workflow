import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import vm from 'node:vm';
import {untilAborted} from '../../gui/managementCommand.js';
import {requestErrorMessage} from '../../gui/requestError.mjs';

test('생성 제안 조회 시간 초과 직후 종료하면 상태를 갱신하지 않는다',async()=>{
 const source=readFileSync(new URL('../../gui/GenerationProposal.jsx',import.meta.url),'utf8');
 const code=source.slice(source.indexOf('  async function inspect()'),source.indexOf('  return <section',source.indexOf('  async function inspect()')));
 let timeout,updates=0;const request={current:null};
 const context=vm.createContext({AbortController,request,session:'s',job:'j',snapshot:'h',offset:0,kind:'video',readGenerationProposal:()=>{},setTimeout:fn=>(timeout=fn,1),clearTimeout:()=>{},setBusy:()=>updates++,setError:()=>updates++,setProposal:()=>updates++,readProposalPreview:(_fn,_args,signal)=>untilAborted(new Promise(()=>{}),signal),requestErrorMessage});
 vm.runInContext(code,context);const pending=context.inspect();timeout();const controller=request.current;request.current=null;controller.abort();const before=updates;await pending;assert.equal(updates,before);
});

test('생성 제안 연결 실패 뒤 재조회하면 결과와 대기 해제가 복구된다',async()=>{
 const source=readFileSync(new URL('../../gui/GenerationProposal.jsx',import.meta.url),'utf8');
 const code=source.slice(source.indexOf('  async function inspect()'),source.indexOf('  return <section',source.indexOf('  async function inspect()')));
 let attempts=0,error='',busy=false,result=null;const request={current:null},body={};
 const context=vm.createContext({AbortController,request,session:'s',job:'j',snapshot:'h',offset:0,kind:'audio',readGenerationProposal:()=>{},setTimeout,clearTimeout,requestErrorMessage,document:{body,activeElement:body},buttonRef:{current:null},requestAnimationFrame:()=>{},setBusy:value=>busy=value,setError:value=>error=value,setProposal:value=>result=value,readProposalPreview:async()=>{if(++attempts===1)throw new TypeError('Failed to fetch');return {service:'music-heartmula'};}});
 vm.runInContext(code,context);await context.inspect();assert.match(error,/연결 상태를 확인/);assert.equal(busy,false);assert.equal(request.current,null);
 await context.inspect();assert.equal(error,'');assert.equal(result.service,'music-heartmula');assert.equal(busy,false);assert.equal(attempts,2);
});

test('접수폼 자동 조회 복구는 별도 제안 오류를 지우지 않는다',async()=>{
 const source=readFileSync(new URL('../../gui/GenerationProposal.jsx',import.meta.url),'utf8');
 const start=source.indexOf('    async function refresh()');const end=source.indexOf('    refresh();',start);const code=source.slice(start,end);assert.ok(start>=0&&end>start);
 let calls=0,pollError='',manualError='제안 오류';const context=vm.createContext({active:true,timer:null,attempts:0,controller:new AbortController(),session:'s',job:'j',snapshot:'h',offset:0,kind:'video',untilAborted,requestErrorMessage,managementCommand:async()=>{if(++calls===1)throw new TypeError('Failed to fetch');return {forms:[]};},setPollError:value=>pollError=value,setError:value=>manualError=value,setPrepared:()=>{},setTimeout:()=>1});
 vm.runInContext(code,context);await context.refresh();assert.match(pollError,/연결 상태를 확인/);await context.refresh();assert.equal(pollError,'');assert.equal(manualError,'제안 오류');
});
