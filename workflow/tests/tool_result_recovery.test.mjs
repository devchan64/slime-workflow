import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import vm from 'node:vm';
import {untilAborted} from '../../gui/managementCommand.js';
import {requestErrorMessage} from '../../gui/requestError.mjs';

test('도구 결과 조회는 연결 실패와 시간 초과에 재조회 가능한 오류를 표시한다',async()=>{
 const source=readFileSync(new URL('../../gui/app.jsx',import.meta.url),'utf8');
 const start=source.indexOf('  useEffect(()=>{if(!result?.call_id)return;',source.indexOf('function ToolResultPanel'));const end=source.indexOf('  const full=',start);assert.ok(start>=0&&end>start);
 for(const mode of ['network','timeout']){
  let timer,error='',cleanup;const context=vm.createContext({useEffect:fn=>cleanup=fn(),result:{call_id:'call'},job:'job',session:'session',revision:0,AbortController,untilAborted,requestErrorMessage,setTimeout:fn=>(timer=fn,1),clearTimeout:()=>{},setData:()=>{},setError:value=>error=value,managementCommand:()=>mode==='network'?Promise.reject(new TypeError('Failed to fetch')):new Promise(()=>{})});
  vm.runInContext(source.slice(start,end),context);if(mode==='timeout')timer();await new Promise(done=>setImmediate(done));assert.match(error,mode==='timeout'?/시간이 초과/:/연결 상태를 확인/);cleanup();
 }
});

test('도구 결과 화면을 닫은 뒤 늦은 응답은 표시하지 않는다',async()=>{
 const source=readFileSync(new URL('../../gui/app.jsx',import.meta.url),'utf8');
 const start=source.indexOf('  useEffect(()=>{if(!result?.call_id)return;',source.indexOf('function ToolResultPanel'));const end=source.indexOf('  const full=',start);assert.ok(start>=0&&end>start);
 let finish,cleanup,updates=0;const context=vm.createContext({useEffect:fn=>cleanup=fn(),result:{call_id:'call'},job:'job',session:'session',revision:0,AbortController,untilAborted,requestErrorMessage,setTimeout,clearTimeout,setData:()=>updates++,setError:()=>updates++,managementCommand:()=>new Promise(resolve=>finish=resolve)});
 vm.runInContext(source.slice(start,end),context);cleanup();const before=updates;finish({id:'job',call_id:'call',output:'늦은 결과'});await new Promise(done=>setImmediate(done));assert.equal(updates,before);
});
