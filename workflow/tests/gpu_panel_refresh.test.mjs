import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import vm from 'node:vm';
import {requestErrorMessage} from '../../gui/requestError.mjs';

const source=readFileSync(new URL('../../gui/GpuPanel.jsx',import.meta.url),'utf8');
test('GPU 상태 수동·자동 갱신은 렌더 전 중복 요청을 막는다',()=>{
 const code=source.slice(source.indexOf('  function requestRefresh()'),source.indexOf('  const live='));
 let requests=0,loading=false;const pending={current:false};
 const context=vm.createContext({pending,setLoading:value=>loading=value,setRevision:()=>requests++});
 vm.runInContext(code,context);context.requestRefresh();context.requestRefresh();
 assert.equal(requests,1);assert.equal(pending.current,true);assert.equal(loading,true);
});

test('GPU 프로세스의 손상된 표시 값은 이전 상태를 보존하고 오류를 알린다',async()=>{
 const effect=source.slice(source.indexOf('  useEffect(() => {'),source.indexOf('  const processes ='));
 for(const process of [{command:{}},{id:[]},{pid:{}},{gpu_parent_pid:{}}]){
  let cleanup,error='',status={status:'idle',processes:[]};
  const context=vm.createContext({AbortController,TypeError,requestErrorMessage,pending:{current:true},revision:0,useEffect:fn=>cleanup=fn(),setTimeout:()=>1,clearTimeout:()=>{},setLoading:()=>{},setStatus:value=>status=value,setCheckedAt:()=>{},setError:value=>error=value,fetch:async()=>({ok:true,json:async()=>({status:'busy',processes:[process]})})});
  vm.runInContext(effect,context);await new Promise(done=>setImmediate(done));
  assert.match(error,/프로세스 목록/);assert.equal(status.status,'idle');cleanup();
 }
});

test('GPU 상태 조회의 메시지 없는 오류 뒤 재조회가 복구된다',async()=>{
 const effect=source.slice(source.indexOf('  useEffect(() => {'),source.indexOf('  const processes ='));
 let cleanup,error='',loading=true,status=null,calls=0;const pending={current:true};
 const context=vm.createContext({AbortController,TypeError,requestErrorMessage,pending,revision:0,useEffect:fn=>cleanup=fn(),setTimeout:()=>1,clearTimeout:()=>{},setLoading:value=>loading=value,setStatus:value=>status=value,setCheckedAt:()=>{},setError:value=>error=value,fetch:()=>++calls===1?Promise.reject(null):Promise.resolve({ok:true,json:async()=>({status:'idle',processes:[]})})});
 vm.runInContext(effect,context);await new Promise(done=>setImmediate(done));
 assert.ok(error);assert.equal(loading,false);assert.equal(pending.current,false);
 cleanup();pending.current=true;context.revision=1;vm.runInContext(effect,context);await new Promise(done=>setImmediate(done));
 assert.equal(error,'');assert.equal(status.status,'idle');assert.equal(pending.current,false);cleanup();
});
