import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import vm from 'node:vm';
import {untilAborted} from '../../gui/managementCommand.js';

const source=readFileSync(new URL('../../gui/SavedGeneratorInputs.jsx',import.meta.url),'utf8');
const effect=source.slice(source.indexOf('  useEffect(()=>{\n    let active=true,timedOut=false;'),source.indexOf('  if(state.id!==id'));
test('공통 저장 입력 조회는 별도 조회 함수와 기본 조회 모두 지연되면 복구한다',async()=>{
 for(const custom of [false,true]){
  let timer,close,finish,state;const delayed=new Promise(done=>finish=done);
  const context=vm.createContext({AbortController,untilAborted,useEffect:fn=>close=fn(),reader:{current:custom?()=>delayed:null},managementCommand:()=>delayed,service:'service',statusCommand:'status',id:'job',revision:0,setState:value=>state=value,setTimeout:fn=>(timer=fn,1),clearTimeout:()=>{},requestErrorMessage:e=>e.message});
  vm.runInContext(effect,context);timer();await new Promise(done=>setImmediate(done));
  assert.match(state.error,/시간이 초과/);finish({id:'job',request:{prompt:'늦은 결과'}});await new Promise(done=>setImmediate(done));assert.match(state.error,/시간이 초과/);close();
 }
});
test('저장 입력 조회는 배열 형태의 손상된 요청을 거부한다',async()=>{
 let state;const context=vm.createContext({AbortController,untilAborted,useEffect:fn=>fn(),reader:{current:async()=>({id:'job',request:[]})},service:'service',statusCommand:'status',id:'job',revision:0,setState:value=>state=value,setTimeout:()=>1,clearTimeout:()=>{},requestErrorMessage:e=>e.message});
 vm.runInContext(effect,context);await new Promise(done=>setImmediate(done));assert.match(state.error,/일치하지/);
});
test('저장 입력 재조회 초점은 대상 서비스가 바뀌면 복구하지 않는다',()=>{
 const focus=source.slice(source.indexOf('  useEffect(()=>{\n    if(!restoreFocus.current'),source.indexOf('  useEffect(()=>{\n    let active=true'));
 for(const same of [false,true]){
  const body={};let frame,focused=0;const restoreFocus={current:true};
  const context=vm.createContext({useEffect:fn=>fn(),restoreFocus,state:{id:'job',service:'old',statusCommand:'status',loading:false},id:'job',service:same?'old':'new',statusCommand:'status',document:{body,activeElement:body},requestAnimationFrame:fn=>frame=fn,resultRef:{current:{isConnected:true,focus:()=>focused++}}});
  vm.runInContext(focus,context);if(frame)frame();assert.equal(focused,same?1:0);
 }
 const cleanup=source.match(/useEffect\(\(\)=>\(\)=>\{restoreFocus\.current=false;\},\[id,service,statusCommand\]\);/)[0];
 const ref={current:true};let stop;vm.runInContext(cleanup,vm.createContext({useEffect:fn=>stop=fn(),restoreFocus:ref,id:'job',service:'service',statusCommand:'status'}));stop();assert.equal(ref.current,false);
});
test('저장 입력 시간 초과 후 재조회 성공은 늦은 이전 응답을 무시한다',async()=>{
 let timer,stop,finish,state,calls=0;const delayed=new Promise(done=>finish=done);
 const context=vm.createContext({AbortController,untilAborted,useEffect:fn=>stop=fn(),reader:{current:()=>++calls===1?delayed:Promise.resolve({id:'job',request:{prompt:'새 결과'}})},service:'service',statusCommand:'status',id:'job',revision:0,setState:value=>state=value,setTimeout:fn=>(timer=fn,1),clearTimeout:()=>{},requestErrorMessage:e=>e.message});
 vm.runInContext(effect,context);timer();await new Promise(done=>setImmediate(done));assert.match(state.error,/시간이 초과/);
 stop();context.revision=1;vm.runInContext(effect,context);await new Promise(done=>setImmediate(done));assert.equal(state.request.prompt,'새 결과');
 finish({id:'job',request:{prompt:'이전 결과'}});await new Promise(done=>setImmediate(done));assert.equal(state.request.prompt,'새 결과');stop();
});
test('저장 입력 초점 예약 후 화면 전환은 예약을 취소한다',()=>{
 const focus=source.slice(source.indexOf('  useEffect(()=>{\n    if(!restoreFocus.current'),source.indexOf('  useEffect(()=>{\n    let active=true'));
 let stop,cancelled=null;const body={};
 const context=vm.createContext({useEffect:fn=>stop=fn(),restoreFocus:{current:true},state:{id:'job',service:'old',statusCommand:'status',loading:false},id:'job',service:'old',statusCommand:'status',document:{body,activeElement:body},requestAnimationFrame:()=>7,cancelAnimationFrame:id=>cancelled=id,resultRef:{current:{isConnected:true,focus:()=>{}}}});
 vm.runInContext(focus,context);stop();assert.equal(cancelled,7);
});
