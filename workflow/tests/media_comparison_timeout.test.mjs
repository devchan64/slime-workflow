import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import vm from 'node:vm';
import {untilAborted} from '../../gui/managementCommand.js';

test('비교 결과 조회는 시간 초과와 화면 종료에 복구된다',async()=>{
 const source=readFileSync(new URL('../../gui/MediaJobResult.jsx',import.meta.url),'utf8');
 for(const [begin,end] of [['function SeamlessComparison','export function CircularComparisonImages'],['function CircularComparison','function SavedPoseVideo']])for(const finish of ['timeout','close']){
  const section=source.slice(source.indexOf(begin),source.indexOf(end));
  const effect=section.slice(section.indexOf('  useEffect(()=>{\n    const controller='),section.indexOf('  if(error)return'));
  let timer,cleanup,error='',loading=false,resolveLate,resultUpdates=0;
  const context=vm.createContext({AbortController,untilAborted,id:'job',revision:0,useEffect:fn=>cleanup=fn(),
   setTimeout:fn=>(timer=fn,1),clearTimeout:()=>{},fetch:()=>new Promise(resolve=>resolveLate=resolve),
   setLoading:value=>loading=value,setError:value=>error=value,setResult:()=>resultUpdates++,setImages:()=>resultUpdates++});
  vm.runInContext(effect,context);
  if(finish==='timeout')timer();else cleanup();
  resolveLate({ok:true,json:async()=>({images:[],method:'test'})});await new Promise(resolve=>setImmediate(resolve));
  assert.equal(resultUpdates,0);
  if(finish==='timeout'){assert.match(error,/시간이 초과/);assert.equal(loading,false);}else assert.equal(error,'');
 }
});
