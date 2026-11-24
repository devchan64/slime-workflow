import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import vm from 'node:vm';
import {untilAborted} from '../../gui/managementCommand.js';
import {mediaResultErrorMessage,validMediaResultDetails} from '../../gui/mediaResultValidation.mjs';
import {validGenerationEstimate} from '../../gui/generationEstimate.mjs';

test('비교 결과 조회는 시간 초과와 화면 종료에 복구된다',async()=>{
 const source=readFileSync(new URL('../../gui/MediaJobResult.jsx',import.meta.url),'utf8');
 for(const [begin,end] of [['function SeamlessComparison','export function CircularComparisonImages'],['function CircularComparison','function SavedPoseVideo']])for(const finish of ['timeout','close']){
  const section=source.slice(source.indexOf(begin),source.indexOf(end));
  const effect=section.slice(section.indexOf('  useEffect(()=>{\n    const controller='),section.indexOf('  if(error)return'));
  let timer,cleanup,error='',loading=false,resolveLate,resultUpdates=0;
  const context=vm.createContext({AbortController,untilAborted,mediaResultErrorMessage,id:'job',revision:0,useEffect:fn=>cleanup=fn(),
   setTimeout:fn=>(timer=fn,1),clearTimeout:()=>{},fetch:()=>new Promise(resolve=>resolveLate=resolve),
   setLoading:value=>loading=value,setError:value=>error=value,setResult:()=>resultUpdates++,setImages:()=>resultUpdates++});
  vm.runInContext(effect,context);
  if(finish==='timeout')timer();else cleanup();
  resolveLate({ok:true,json:async()=>({images:[],method:'test'})});await new Promise(resolve=>setImmediate(resolve));
  assert.equal(resultUpdates,0);
  if(finish==='timeout'){assert.match(error,/시간이 초과/);assert.equal(loading,false);}else assert.equal(error,'');
 }
});

test('비교 결과의 중복 이미지 경로는 오류로 처리하고 정상 결과는 표시한다',async()=>{
 const source=readFileSync(new URL('../../gui/MediaJobResult.jsx',import.meta.url),'utf8');
 for(const [begin,end,prefix,name] of [
  ['function SeamlessComparison','export function CircularComparisonImages','/flux-seamless-generator/jobs/job/','tiled-preview.png'],
  ['function CircularComparison','function SavedPoseVideo','/image-generation-21-circular/jobs/job/','result.png'],
 ])for(const duplicate of [true,false]){
  const section=source.slice(source.indexOf(begin),source.indexOf(end));
  const effect=section.slice(section.indexOf('  useEffect(()=>{\n    const controller='),section.indexOf('  if(error)return'));
  const image={label:'결과',url:prefix+name}, payload={method:'test',images:duplicate?[image,{...image}]:[image]};
  let error='',loading=false,result;
  const context=vm.createContext({AbortController,untilAborted,mediaResultErrorMessage,id:'job',revision:0,useEffect:fn=>fn(),
   setTimeout:()=>1,clearTimeout:()=>{},fetch:async()=>({ok:true,json:async()=>payload}),
   setLoading:value=>loading=value,setError:value=>error=value,setResult:value=>result=value,setImages:value=>result=value});
  vm.runInContext(effect,context);
  await new Promise(resolve=>setImmediate(resolve));
  assert.equal(loading,false);
  if(duplicate){assert.match(error,/확인/);assert.equal(result,undefined);}
  else{assert.equal(error,'');assert.ok(result);}
 }
});

test('비교 조회가 메시지 없는 오류로 실패해도 대기를 해제하고 재조회 안내를 표시한다',async()=>{
 const source=readFileSync(new URL('../../gui/MediaJobResult.jsx',import.meta.url),'utf8');
 for(const [begin,end] of [['function SeamlessComparison','export function CircularComparisonImages'],['function CircularComparison','function SavedPoseVideo']]){
  const section=source.slice(source.indexOf(begin),source.indexOf(end));
  const effect=section.slice(section.indexOf('  useEffect(()=>{\n    const controller='),section.indexOf('  if(error)return'));
  let error='',loading=false;
  const context=vm.createContext({AbortController,untilAborted,mediaResultErrorMessage,id:'job',revision:0,useEffect:fn=>fn(),setTimeout:()=>1,clearTimeout:()=>{},fetch:()=>Promise.reject(null),setLoading:value=>loading=value,setError:value=>error=value});
  vm.runInContext(effect,context);await new Promise(resolve=>setImmediate(resolve));assert.equal(loading,false);assert.match(error,/불러올 수 없습니다/);
 }
});

test('주 결과 조회는 메시지 없는 오류 뒤 정상 재조회로 복구한다',async()=>{
 const source=readFileSync(new URL('../../gui/MediaJobResult.jsx',import.meta.url),'utf8');
 const section=source.slice(source.indexOf('function MediaJobResultForSelection'));
 const effect=section.slice(section.indexOf('  useEffect(()=>{\n    let active=true,deadline;'),section.indexOf('  const directFolder='));
 let close,loading=false,error='',job=null,ok=false;
 const response={service:'video-service',job_id:'job',job:{status:'running',result_status:'not_ready'}};
 const context=vm.createContext({AbortController,untilAborted,mediaResultErrorMessage,validMediaResultDetails,validGenerationEstimate,document:{activeElement:null},refreshRef:{current:{}},restoreRefreshFocus:{current:false},service:'video-service',id:'job',kind:'video',revision:0,statusCommands:{video:'status'},useEffect:fn=>close=fn(),setTimeout:()=>1,clearTimeout:()=>{},setLoading:value=>loading=value,setError:value=>error=value,setAttemptedAt:()=>{},setCheckedAt:()=>{},setJob:value=>job=value,managementCommand:()=>ok?Promise.resolve(response):Promise.reject(null)});
 vm.runInContext(effect,context);await new Promise(resolve=>setImmediate(resolve));assert.equal(loading,false);assert.match(error,/확인할 수 없습니다/);assert.equal(job,null);
 close();ok=true;context.revision=1;vm.runInContext(effect,context);await new Promise(resolve=>setImmediate(resolve));assert.equal(loading,false);assert.equal(error,'');assert.equal(job.status,'running');close();
});
