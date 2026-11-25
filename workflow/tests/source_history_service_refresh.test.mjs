import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import vm from 'node:vm';
import {untilAborted} from '../../gui/managementCommand.js';

const source=readFileSync(new URL('../../gui/SourceHistory.jsx',import.meta.url),'utf8');
const start=source.indexOf('  useEffect(()=>{\n    const controller=new AbortController();\n    let active=true,timedOut=false;',source.indexOf('export default function SourceHistory'));
const end=source.indexOf('  },[attempt]);',start)+'  },[attempt]);'.length;
test('이력 서비스 조회가 메시지 없이 실패해도 재시도를 안내한다',async()=>{
 for(const problem of [null,new Error('')]){
  let run,error='',loading=true;
  const context=vm.createContext({AbortController,untilAborted,TypeError,setTimeout,clearTimeout,attempt:0,useEffect:fn=>run=fn,fetch:async()=>{throw problem;},setSources:()=>{},select:()=>{},setLoading:value=>loading=value,setError:value=>error=value});
  vm.runInContext(source.slice(start,end),context);const cleanup=run();await new Promise(resolve=>setImmediate(resolve));
  assert.match(error,/다시 시도/);assert.equal(loading,false);cleanup();
 }
});
test('이력 서비스 재조회는 현재 선택이 있으면 유지하고 없으면 첫 서비스를 선택한다',async()=>{
 assert.ok(start>=0 && end>start);
 for(const initial of ['writer-agent','removed']){
  let run,selected=initial,sources;const rows=[{service:'flux',command:'history'},{service:'writer-agent',command:'history'}];
  const context=vm.createContext({AbortController,untilAborted,TypeError,setTimeout,clearTimeout,attempt:0,useEffect:fn=>run=fn,fetch:async()=>({ok:true,json:async()=>rows}),orderHistorySources:value=>value,setSources:value=>sources=value,select:fn=>selected=fn(selected),setLoading:()=>{},setError:()=>{}});
  vm.runInContext(source.slice(start,end),context);const cleanup=run();await new Promise(resolve=>setImmediate(resolve));assert.equal(selected,initial==='writer-agent'?'writer-agent':'flux');assert.equal(sources,rows);cleanup();
 }
});
