import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import vm from 'node:vm';
import {untilAborted} from '../../gui/managementCommand.js';
import {validGeneratorHistoryPage} from '../../gui/generatorHistoryPage.mjs';
import {generationSourceStatusCommand} from '../../gui/generationSourceStatusCommand.mjs';

const source=readFileSync(new URL('../../gui/ActiveGeneratorProgress.jsx',import.meta.url),'utf8');
const effect=source.slice(source.indexOf('  useEffect(()=>{\n    let active=true,deadline;'),source.indexOf('  const activeSummary='));
test('번역 진행 상태는 읽기 전용 상태를 조회하고 작업 ID를 확인한다',async()=>{
 for(const valid of [true,false]){
  let records=null;const calls=[];const page={records:[{id:'job1',recorded_status:'running',status_source:'job'}],offset:0,total:1,snapshot:'a'.repeat(64),unavailable_count:0,next_offset:null};
  const context=vm.createContext({AbortController,untilAborted,validGeneratorHistoryPage,generationSourceStatusCommand,document:{activeElement:null},refreshRef:{current:{}},restoreFocus:{current:false},jobRefs:{current:new Map()},refreshLock:{current:false},service:'prompt-translation',revision:0,refreshKey:0,useEffect:fn=>fn(),setTimeout:()=>1,clearTimeout:()=>{},setLoading:()=>{},setError:()=>{},setRecords:value=>records=value,setTruncated:()=>{},setCheckedAt:()=>{},managementCommand:async(service,command,payload)=>{calls.push({service,command,payload});return command==='history-observe' ? page : {id:valid?'job1':'other',status:{status:'running'}};}});
  vm.runInContext(effect,context);await new Promise(done=>setImmediate(done));
  assert.equal(calls[1].service,'prompt-translation');assert.equal(calls[1].command,'translation-status');assert.equal(calls[1].payload.id,'job1');
  assert.equal(records.length,1);assert.equal(Boolean(records[0].error),!valid);
 }
});
test('수동 및 자동 갱신은 시작 직후 중복을 막고 조회 종료 후 다시 가능하다',()=>{
 const code=source.slice(source.indexOf('  function queueRefresh('),source.indexOf('  const live=useLiveRefresh'));
 const button={};let calls=0,loading=false;const refreshLock={current:false},restoreFocus={current:false};
 const context=vm.createContext({refreshLock,restoreFocus,refreshRef:{current:button},document:{activeElement:button},setLoading:value=>loading=value,refresh:()=>calls++});
 vm.runInContext(code,context);context.queueRefresh(true);context.queueRefresh();assert.equal(calls,1);assert.equal(loading,true);assert.equal(restoreFocus.current,true);
 refreshLock.current=false;context.queueRefresh();assert.equal(calls,2);
});
test('진행 작업은 손상된 이력과 중복 페이지를 빈 목록으로 표시하지 않는다',async()=>{
 const hash='a'.repeat(64),row={id:'job1',recorded_status:'completed',status_source:'job'};
 for(const defect of ['row','offset','duplicate','snapshot','truncated','total','valid']){
  let error='',records='previous',loading=false,calls=0;
  const page={records:[row],offset:0,total:1,snapshot:hash,unavailable_count:0,next_offset:null};
  if(defect==='row')page.records=[{...row,recorded_status:'broken'}];
  if(defect==='offset')page.offset=1;
  if(defect==='snapshot')page.snapshot='bad';
  if(defect==='duplicate' || defect==='total'){page.next_offset=1;page.total=2;}
  if(defect==='truncated')page.total=2;
  const context=vm.createContext({AbortController,untilAborted,validGeneratorHistoryPage,generationSourceStatusCommand,document:{activeElement:null},refreshRef:{current:{}},restoreFocus:{current:false},jobRefs:{current:new Map()},refreshLock:{current:false},service:'service',revision:0,refreshKey:0,useEffect:fn=>fn(),setTimeout:()=>1,clearTimeout:()=>{},setLoading:value=>loading=value,setError:value=>error=value,setRecords:value=>records=value,setTruncated:()=>{},setCheckedAt:()=>{},managementCommand:async()=>{calls++;return calls===1?page:{...page,records:defect==='total'?[{...row,id:'job2'}]:[row],offset:1,total:defect==='total'?3:2,next_offset:defect==='total'?2:null};}});
  vm.runInContext(effect,context);await new Promise(done=>setImmediate(done));
  assert.equal(loading,false);assert.equal(context.refreshLock.current,false);
  if(defect==='valid'){assert.equal(error,'');assert.equal(records.length,0);}else{assert.match(error,/확인하지 못했습니다/);assert.equal(records,'previous');}
 }
});

test('진행 작업 조회 시간 초과 후 갱신 잠금을 해제한다',async()=>{
 let timer,loading=false,error='';const refreshLock={current:false};
 const context=vm.createContext({AbortController,untilAborted,validGeneratorHistoryPage,generationSourceStatusCommand,document:{activeElement:null},refreshRef:{current:{}},restoreFocus:{current:false},jobRefs:{current:new Map()},refreshLock,service:'service',revision:0,refreshKey:0,useEffect:fn=>fn(),setTimeout:fn=>(timer=fn,1),clearTimeout:()=>{},setLoading:value=>loading=value,setError:value=>error=value,managementCommand:()=>new Promise(()=>{})});
 vm.runInContext(effect,context);assert.equal(refreshLock.current,true);timer();await new Promise(done=>setImmediate(done));assert.equal(refreshLock.current,false);assert.equal(loading,false);assert.match(error,/시간이 초과/);
});

test('진행 작업이 목록에서 사라지면 그 행의 초점만 복구 대상으로 표시한다',async()=>{
 for(const focused of ['removed','other','retained']){
  const target={},other={},document={activeElement:focused==='other'?other:target},restoreFocus={current:false};
  const node={contains:value=>value===target};const jobRefs={current:new Map([['job1',node]])};
  const row={id:'job1',recorded_status:focused==='retained'?'running':'completed',status_source:'job'};
  const page={records:[row],offset:0,total:1,snapshot:'a'.repeat(64),unavailable_count:0,next_offset:null};
  const context=vm.createContext({AbortController,untilAborted,validGeneratorHistoryPage,generationSourceStatusCommand,document,refreshRef:{current:{}},restoreFocus,jobRefs,refreshLock:{current:false},service:'service',revision:0,refreshKey:0,useEffect:fn=>fn(),setTimeout:()=>1,clearTimeout:()=>{},setLoading:()=>{},setError:()=>{},setRecords:()=>{},setTruncated:()=>{},setCheckedAt:()=>{},managementCommand:async(_service,command)=>command==='history-observe'?page:{service:'service',job_id:'job1',job:{status:'running'}}});
  vm.runInContext(effect,context);await new Promise(done=>setImmediate(done));assert.equal(restoreFocus.current,focused==='removed');
 }
});
