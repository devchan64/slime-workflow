import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import vm from 'node:vm';
import {untilAborted} from '../../gui/managementCommand.js';
import {requestErrorMessage} from '../../gui/requestError.mjs';

test('음악 예제의 손상된 시간·시드·중복 ID를 거부하고 적용 필드를 제한한다',()=>{
 const source=readFileSync(new URL('../../gui/MusicExamples.jsx',import.meta.url),'utf8');
 const code=source.slice(source.indexOf('export function validMusicExamples'),source.indexOf('export function MusicExampleDetail')).replaceAll('export function','function');
 const context=vm.createContext({});vm.runInContext(code,context);
 const row={id:'a',label:'예제',description:'설명',request:{prompt:'p',lyrics:'l',duration_seconds:30,seed:7,tag:'기존 값 보존'}};
 assert.equal(context.validMusicExamples([row]),true);
 for(const invalid of [[row,row],[{...row,request:{...row.request,duration_seconds:NaN}}],[{...row,request:{...row.request,seed:-1}}]])assert.equal(context.validMusicExamples(invalid),false);
 assert.deepEqual(JSON.parse(JSON.stringify(context.musicExampleInputs(row.request))),{prompt:'p',lyrics:'l',duration_seconds:30,seed:7});
});

test('음악 예제 본문 지연은 시간 초과되고 재조회로 복구된다',async()=>{
 const source=readFileSync(new URL('../../gui/MusicExamples.jsx',import.meta.url),'utf8');
 const start=source.indexOf('  useEffect(()=>{\n    if(!open || examples)return;');
 const end=source.indexOf('  },[open,examples,attempt]);',start)+'  },[open,examples,attempt]);'.length;
 let run,timeout,fail=true,error='',loading=false,examples=null;const retryPending={current:true};
 const context=vm.createContext({AbortController,untilAborted,requestErrorMessage,validMusicExamples:rows=>Array.isArray(rows),open:true,examples:null,attempt:0,retryPending,useEffect:fn=>run=fn,setError:value=>error=value,setLoading:value=>loading=value,setExamples:value=>examples=value,select:()=>{},
  setTimeout:fn=>{timeout=fn;return 1;},clearTimeout:()=>{},fetch:async()=>({ok:true,json:()=>fail ? new Promise(()=>{}) : Promise.resolve([{id:'a',label:'예제',request:{prompt:'p',lyrics:'l'}}])})});
 vm.runInContext(source.slice(start,end),context);const cleanup=run();await new Promise(resolve=>setImmediate(resolve));timeout();await new Promise(resolve=>setImmediate(resolve));
 assert.match(error,/시간이 초과/);assert.equal(loading,false);assert.equal(retryPending.current,false);assert.equal(examples,null);
 cleanup();fail=false;run();await new Promise(resolve=>setImmediate(resolve));
 assert.equal(error,'');assert.equal(loading,false);assert.equal(examples[0].id,'a');
});

test('음악 예제 영역을 닫으면 늦은 응답이 상태를 변경하지 않는다',async()=>{
 const source=readFileSync(new URL('../../gui/MusicExamples.jsx',import.meta.url),'utf8');
 const start=source.indexOf('  useEffect(()=>{\n    if(!open || examples)return;');
 const end=source.indexOf('  },[open,examples,attempt]);',start)+'  },[open,examples,attempt]);'.length;
 let run,resolveBody,updates=0;const body=new Promise(resolve=>resolveBody=resolve);
 const context=vm.createContext({AbortController,untilAborted,requestErrorMessage,validMusicExamples:()=>true,open:true,examples:null,attempt:0,retryPending:{current:true},useEffect:fn=>run=fn,
  setError:()=>updates++,setLoading:()=>updates++,setExamples:()=>updates++,select:()=>updates++,setTimeout:()=>1,clearTimeout:()=>{},fetch:async()=>({ok:true,json:()=>body})});
 vm.runInContext(source.slice(start,end),context);const cleanup=run();await new Promise(resolve=>setImmediate(resolve));cleanup();const before=updates;
 resolveBody([{id:'a'}]);await new Promise(resolve=>setImmediate(resolve));assert.equal(updates,before);
});
