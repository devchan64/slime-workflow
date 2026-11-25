import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import vm from 'node:vm';
import {untilAborted} from '../../gui/managementCommand.js';
import {validModelInventory} from '../../gui/modelInventoryValidation.mjs';
import {requestErrorMessage} from '../../gui/requestError.mjs';

const source=readFileSync(new URL('../../gui/ModelInventory.jsx',import.meta.url),'utf8');
test('모델 파일 목록은 수동 조회를 시작하자마자 중복을 막는다',()=>{
 const code=source.slice(source.indexOf('  function requestRefresh()'),source.indexOf('  const live=useLiveRefresh'));
 let calls=0,loading=false;const pending={current:false};const context=vm.createContext({pending,setLoading:value=>loading=value,refresh:()=>calls++});
 vm.runInContext(code,context);context.requestRefresh();context.requestRefresh();assert.equal(calls,1);assert.equal(pending.current,true);assert.equal(loading,true);
});
test('모델 파일 목록 조회는 메시지 없는 오류 후 정상 응답으로 복구한다',async()=>{
 const effect=source.slice(source.indexOf('  useEffect(() => {'),source.indexOf('  return <div ref={live.ref}>'));
 let cleanup,timers=[],error='',loading=false,inventory=null,success=false,calls=0;const pending={current:false};
 const model={files:[],count:0,total_bytes:0,truncated:false,incomplete:false};
 const context=vm.createContext({AbortController,untilAborted,validModelInventory,requestErrorMessage,pending,service:'service',revision:0,useEffect:fn=>cleanup=fn(),setTimeout:fn=>(timers.push(fn),timers.length),clearTimeout:()=>{},setLoading:value=>loading=value,setError:value=>error=value,setInventory:value=>inventory=value,setCheckedAt:()=>{},managementCommand:()=>{calls++;return success?Promise.resolve({models:{service:model}}):Promise.reject(null);}});
 vm.runInContext(effect,context);await new Promise(done=>setImmediate(done));assert.equal(loading,false);assert.equal(pending.current,false);assert.match(error,/조회할 수 없습니다/);
 cleanup();success=true;context.revision=1;vm.runInContext(effect,context);await new Promise(done=>setImmediate(done));assert.equal(error,'');assert.equal(inventory,model);assert.equal(pending.current,false);cleanup();assert.equal(calls,2);
});

test('모델 파일 목록 연결 오류는 확인 방법을 표시한다',async()=>{
 const effect=source.slice(source.indexOf('  useEffect(() => {'),source.indexOf('  return <div ref={live.ref}>'));
 let cleanup,error='';const context=vm.createContext({AbortController,untilAborted,validModelInventory,requestErrorMessage,pending:{current:false},service:'service',revision:0,useEffect:fn=>cleanup=fn(),setTimeout:()=>1,clearTimeout:()=>{},setLoading:()=>{},setError:value=>error=value,setInventory:()=>{},setCheckedAt:()=>{},managementCommand:()=>Promise.reject(new TypeError('Failed to fetch'))});
 vm.runInContext(effect,context);await new Promise(done=>setImmediate(done));assert.match(error,/서버에 연결할 수 없습니다.*연결 상태/);cleanup();
});

test('파일 목록 조회 시간 초과는 이전 결과를 보존하고 늦은 응답을 무시한다',async()=>{
 const effect=source.slice(source.indexOf('  useEffect(() => {'),source.indexOf('  return <div ref={live.ref}>'));
 const old={files:[],count:0,total_bytes:0,truncated:false,incomplete:false};
 const newer={files:[{path:'file',bytes:1}],count:1,total_bytes:1,truncated:false,incomplete:false};
 let cleanup,timer,resolve,inventory=old,error='',loading=false;const pending={current:false};
 const response=new Promise(done=>resolve=done);
 const context=vm.createContext({AbortController,untilAborted,validModelInventory,pending,service:'service',revision:0,useEffect:fn=>cleanup=fn(),setTimeout:fn=>(timer=fn,1),clearTimeout:()=>{},setLoading:value=>loading=value,setError:value=>error=value,setInventory:value=>inventory=value,setCheckedAt:()=>{},managementCommand:()=>response});
 vm.runInContext(effect,context);assert.equal(loading,true);assert.equal(pending.current,true);timer();await new Promise(done=>setImmediate(done));
 assert.equal(loading,false);assert.equal(pending.current,false);assert.equal(inventory,old);assert.match(error,/시간이 초과/);
 resolve({models:{service:newer}});await new Promise(done=>setImmediate(done));assert.equal(inventory,old);cleanup();
});
