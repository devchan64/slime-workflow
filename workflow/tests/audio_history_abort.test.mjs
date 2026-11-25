import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import vm from 'node:vm';
import {untilAborted} from '../../gui/managementCommand.js';

test('오디오 저장 입력 조회는 이력 종료 신호를 전달받아 즉시 중단한다',async()=>{
 const source=readFileSync(new URL('../../gui/SoundEffectPage.jsx',import.meta.url),'utf8');
 const code=source.slice(source.indexOf('  async function readJob('),source.indexOf('  function cleaned('));
 let fetchSignal;const context=vm.createContext({AbortController,untilAborted,setTimeout,clearTimeout,formRef:{current:{}},reviewEpoch:{current:0},document:{activeElement:null},formPath:'/input',music:false,
  fetch:(_url,options)=>{fetchSignal=options.signal;return new Promise(()=>{});}});
 vm.runInContext(code,context);const controller=new AbortController();const pending=context.readJob('id',{signal:controller.signal});controller.abort();
 await assert.rejects(pending,error=>error.name==='AbortError');assert.equal(fetchSignal.aborted,true);
});

test('오디오 이력 복원 초점은 사용자의 이동과 새 검토를 존중한다',()=>{
 const source=readFileSync(new URL('../../gui/SoundEffectPage.jsx',import.meta.url),'utf8');
 const start=source.indexOf('restore={(input,record)=>{');
 const end=source.indexOf('}} renderResult=',start);
 const code=source.slice(start+'restore={'.length,end+1);assert.ok(start>=0 && end>start);
 for(const scenario of ['restore','moved','review']){
  let frame,focused=0;const body={},origin={},other={},document={body,activeElement:origin},form={},card={open:false};
  const context=vm.createContext({document,reviewEpoch:{current:0},interactionRef:{current:{busy:false,review:null}},formRef:{current:form},restoreFrame:{current:null},promptRef:{current:{isConnected:true,disabled:false,closest:()=>card,focus:()=>focused++}},
   setForm:()=>{},setNotice:()=>{},cancelAnimationFrame:()=>{},requestAnimationFrame:fn=>(frame=fn,1),record:{reviewAtStart:0,formAtStart:form,focusAtStart:origin}});
  vm.runInContext('globalThis.restore='+code,context);context.restore({},context.record);assert.equal(card.open,true);
  document.activeElement=scenario==='moved'?other:body;if(scenario==='review')context.reviewEpoch.current++;frame();
  assert.equal(focused,scenario==='restore'?1:0,scenario);
 }
});

test('오디오 이력 조회 중 입력이나 검토가 바뀌면 현재 입력을 보존한다',()=>{
 const source=readFileSync(new URL('../../gui/SoundEffectPage.jsx',import.meta.url),'utf8');
 const start=source.indexOf('restore={(input,record)=>{'),end=source.indexOf('}} renderResult=',start);
 const code=source.slice(start+'restore={'.length,end+1);
 for(const scenario of ['edit','review']){
  let applied=0;const original={},formRef={current:scenario==='edit'?{}:original};
  const context=vm.createContext({reviewEpoch:{current:scenario==='review'?1:0},interactionRef:{current:{busy:false,review:null}},formRef,setForm:()=>applied++});
  vm.runInContext('globalThis.restore='+code,context);
  assert.throws(()=>context.restore({},{reviewAtStart:0,formAtStart:original}),/적용하지 않았습니다/);assert.equal(applied,0);
 }
});

test('오디오 저장 입력의 손상된 응답은 복원 대상으로 반환하지 않는다',async()=>{
 const source=readFileSync(new URL('../../gui/SoundEffectPage.jsx',import.meta.url),'utf8');
 const code=source.slice(source.indexOf('  async function readJob('),source.indexOf('  function cleaned('));
 const context=vm.createContext({AbortController,untilAborted,setTimeout,clearTimeout,formRef:{current:{}},reviewEpoch:{current:0},document:{activeElement:null},formPath:'/input',music:true,
  fetch:async()=>({ok:true,json:async()=>({id:'id',request:{prompt:'p',seed:1,loop_request:false,tag:'',lyrics:'l',duration_seconds:null}})})});
 vm.runInContext(code,context);await assert.rejects(context.readJob('id'),/형식을 확인/);
});

test('오디오 저장 입력의 요청·본문 지연 후 재조회는 정상 입력을 반환한다',async()=>{
 const source=readFileSync(new URL('../../gui/SoundEffectPage.jsx',import.meta.url),'utf8');
 const code=source.slice(source.indexOf('  async function readJob('),source.indexOf('  function cleaned('));
 for(const stage of ['request','body']){
  let timer,fail=true;const input={prompt:'p',seed:1,loop_request:false,tag:'',lyrics:'l',duration_seconds:30};
  const context=vm.createContext({AbortController,untilAborted,formRef:{current:{}},reviewEpoch:{current:0},document:{activeElement:null},formPath:'/input',music:true,
   setTimeout:fn=>(timer=fn,1),clearTimeout:()=>{},fetch:()=>fail && stage==='request'?new Promise(()=>{}):Promise.resolve({ok:true,json:()=>fail && stage==='body'?new Promise(()=>{}):Promise.resolve({id:'id',request:input})})});
  vm.runInContext(code,context);const first=context.readJob('id');await new Promise(resolve=>setImmediate(resolve));timer();await assert.rejects(first,/시간이 초과/);
  fail=false;const result=await context.readJob('id');assert.equal(result.request,input,stage);
 }
});
