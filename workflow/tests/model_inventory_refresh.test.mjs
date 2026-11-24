import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import vm from 'node:vm';
import {untilAborted} from '../../gui/managementCommand.js';
import {validModelInventory} from '../../gui/modelInventoryValidation.mjs';

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
 const context=vm.createContext({AbortController,untilAborted,validModelInventory,pending,service:'service',revision:0,useEffect:fn=>cleanup=fn(),setTimeout:fn=>(timers.push(fn),timers.length),clearTimeout:()=>{},setLoading:value=>loading=value,setError:value=>error=value,setInventory:value=>inventory=value,setCheckedAt:()=>{},managementCommand:()=>{calls++;return success?Promise.resolve({models:{service:model}}):Promise.reject(null);}});
 vm.runInContext(effect,context);await new Promise(done=>setImmediate(done));assert.equal(loading,false);assert.equal(pending.current,false);assert.match(error,/조회할 수 없습니다/);
 cleanup();success=true;context.revision=1;vm.runInContext(effect,context);await new Promise(done=>setImmediate(done));assert.equal(error,'');assert.equal(inventory,model);assert.equal(pending.current,false);cleanup();assert.equal(calls,2);
});
