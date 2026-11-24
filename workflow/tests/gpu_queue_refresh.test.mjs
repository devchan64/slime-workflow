import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import vm from 'node:vm';
import {untilAborted} from '../../gui/managementCommand.js';
import {formatGpuQueueSummary} from '../../gui/gpuQueueSummary.mjs';

const source=readFileSync(new URL('../../gui/GpuQueueSummary.jsx',import.meta.url),'utf8');
test('GPU 대기열 재조회는 렌더 전 중복 입력을 막는다',()=>{
 const code=source.slice(source.indexOf('  function refreshQueue()'),source.indexOf('  useEffect(()=>'));
 let calls=0,loading=false;const pending={current:false};
 const context=vm.createContext({pending,setLoading:value=>loading=value,setRevision:()=>calls++});
 vm.runInContext(code,context);context.refreshQueue();context.refreshQueue();
 assert.equal(calls,1);assert.equal(loading,true);assert.equal(pending.current,true);
});
test('GPU 대기열 오류 후 재조회하면 마지막 결과와 오류가 복구된다',async()=>{
 const effect=source.slice(source.indexOf('  useEffect(()=>'),source.indexOf('  return <div'));
 let cleanup,error='',gpu='',failed=false,calls=0;const pending={current:true};
 const context=vm.createContext({AbortController,untilAborted,formatGpuQueueSummary,pending,revision:0,useEffect:fn=>cleanup=fn(),setTimeout:()=>1,clearTimeout:()=>{},setLoading:()=>{},setError:value=>error=value,setGpu:value=>gpu=value,setCheckedAt:()=>{},setFailed:value=>failed=value,fetch:()=>++calls===1?Promise.reject(Error('offline')):Promise.resolve({ok:true,json:async()=>({jobs:[],gpu_status:{status:'idle'}})})});
 vm.runInContext(effect,context);await new Promise(done=>setImmediate(done));
 assert.match(error,/조회하지 못했습니다/);assert.equal(failed,true);assert.equal(pending.current,false);
 cleanup();context.revision=1;pending.current=true;vm.runInContext(effect,context);await new Promise(done=>setImmediate(done));
 assert.equal(error,'');assert.match(gpu,/GPU 유휴/);assert.equal(failed,false);assert.equal(pending.current,false);cleanup();
});
