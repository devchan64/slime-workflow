import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import vm from 'node:vm';
import {untilAborted} from '../../gui/managementCommand.js';
import {validGeneratorHistoryPage} from '../../gui/generatorHistoryPage.mjs';
import {requestErrorMessage} from '../../gui/requestError.mjs';

test('이력 화면 종료 후 늦은 요청은 초점 복구를 예약하지 않는다',async()=>{
 const source=readFileSync(new URL('../../gui/GeneratorHistory.jsx',import.meta.url),'utf8');
 const method=source.slice(source.indexOf('  async function perform('),source.indexOf('  async function list('));
 let finish,timers=0,changes=0;const body={},button={closest:()=>null},document={body,activeElement:button},mounted={current:true};
 const context=vm.createContext({document,pending:{current:false},mounted,focusTimer:{current:null},detailsRef:{current:{contains:()=>true}},searchRef:{current:null},setBusyInSelection:()=>{},setBusy:()=>changes++,setError:()=>changes++,setErrorScope:()=>{},requestErrorMessage,setTimeout:()=>timers++,clearTimeout:()=>{}});
 vm.runInContext(method,context);const task=context.perform(()=>new Promise(resolve=>finish=resolve));mounted.current=false;const before=changes;finish();await task;
 assert.equal(timers,0);assert.equal(changes,before);
});

test('이력 페이지 이동 후 비활성화된 버튼 대신 사용 가능한 버튼에 초점을 복구한다',async()=>{
 const source=readFileSync(new URL('../../gui/GeneratorHistory.jsx',import.meta.url),'utf8');
 const method=source.slice(source.indexOf('  async function perform('),source.indexOf('  async function list('));
 for(const moved of [false,true]){
  let timer,focusedCount=0;const body={},other={},document={body,activeElement:null};
  const target={focus:()=>focusedCount++},button={isConnected:true,disabled:true,closest:selector=>selector==='.generator-history-pagination'};document.activeElement=button;
  const context=vm.createContext({document,pending:{current:false},mounted:{current:true},focusTimer:{current:null},detailsRef:{current:{contains:node=>node===button,querySelector:()=>target}},searchRef:{current:null},setBusyInSelection:()=>{},setBusy:()=>{},setError:()=>{},setErrorScope:()=>{},requestErrorMessage,setTimeout:fn=>(timer=fn,1),clearTimeout:()=>{}});
  vm.runInContext(method,context);await context.perform(async()=>{});document.activeElement=moved?other:body;timer();assert.equal(focusedCount,moved?0:1);
 }
});

test('이력 요약의 손상된 항목은 제외하고 일부 확인 불가를 표시한다',async()=>{
 const source=readFileSync(new URL('../../gui/GeneratorHistory.jsx',import.meta.url),'utf8');
 const effect=source.slice(source.indexOf('  useEffect(()=>{\n    setSummaries({})'),source.indexOf('  async function perform('));
 const good='2026-11-24_12-34-56-1234abcd',bad='2026-11-24_12-34-57-1234abcd';let summaries,notice='',cleanup;
 const context=vm.createContext({AbortController,untilAborted,page:{records:[{id:good},{id:bad}]},service:'service',useEffect:fn=>cleanup=fn(),setSummaries:value=>summaries=value,setSummaryVersion:()=>{},setSummaryNotice:value=>notice=value,setTimeout:()=>1,clearTimeout:()=>{},fetch:async()=>({ok:true,json:async()=>({summaries:{[good]:{width:1024},[bad]:[]}})})});
 vm.runInContext(effect,context);await new Promise(done=>setImmediate(done));
 assert.equal(summaries[good].width,1024);assert.equal(Object.hasOwn(summaries,bad),false);assert.match(notice,/일부 저장 입력 요약/);cleanup();
});

test('이력 요약 조회가 종료된 뒤 늦은 응답은 카드에 반영되지 않는다',async()=>{
 const source=readFileSync(new URL('../../gui/GeneratorHistory.jsx',import.meta.url),'utf8');
 const effect=source.slice(source.indexOf('  useEffect(()=>{\n    setSummaries({})'),source.indexOf('  async function perform('));
 const id='2026-11-24_12-34-56-1234abcd';let finish,cleanup,updates=0,notices=0;
 const context=vm.createContext({AbortController,untilAborted,page:{records:[{id}]},service:'service',useEffect:fn=>cleanup=fn(),setSummaries:()=>updates++,setSummaryVersion:()=>updates++,setSummaryNotice:()=>notices++,setTimeout:()=>1,clearTimeout:()=>{},fetch:()=>new Promise(resolve=>finish=resolve)});
 vm.runInContext(effect,context);cleanup();const initialUpdates=updates,initialNotices=notices;
 finish({ok:true,json:async()=>({summaries:{[id]:{width:1024}}})});await new Promise(done=>setImmediate(done));
 assert.equal(updates,initialUpdates);assert.equal(notices,initialNotices);
});

test('이력 페이지 응답이 손상되면 기존 선택과 목록을 유지한다',async()=>{
 const source=readFileSync(new URL('../../gui/GeneratorHistory.jsx',import.meta.url),'utf8');
 const method=source.slice(source.indexOf('  async function list('),source.indexOf('  function deleted('));
 const previous={records:[{id:'old',recorded_status:'completed'}],total:1,offset:0,next_offset:null,snapshot:'a'.repeat(64)};
 let selected={id:'old'},page=previous,job={id:'old',request:{}};
 const context=vm.createContext({AbortController,untilAborted,validGeneratorHistoryPage,requestErrorMessage,page,pageSize:10,resultId:'',externalResultId:'',expanded:null,service:'service',listRequest:{current:null},cancelLookup:()=>{},setTimeout:()=>1,clearTimeout:()=>{},managementCommand:async()=>({records:[{id:'bad',recorded_status:'completed'}],total:3,offset:0,next_offset:null,snapshot:'a'.repeat(64)}),setSelected:fn=>selected=fn(selected),setJob:fn=>job=fn(job),setPage:value=>page=value,setFilter:()=>{},setPageSize:()=>{},setResultLookup:()=>{}});
 vm.runInContext(method,context);await assert.rejects(context.list(0,''),/이전 이력과 선택을 유지/);
 assert.equal(page,previous);assert.equal(selected.id,'old');assert.equal(job.id,'old');
});

test('이력 밖 결과 재조회는 초점이 결과 안에 있을 때만 복구를 예약한다',()=>{
 const source=readFileSync(new URL('../../gui/GeneratorHistory.jsx',import.meta.url),'utf8');
 const method=source.slice(source.indexOf('  function retryResultLookup()'),source.indexOf('  useEffect(()=>{\n    if(!focusOpenedResult.current'));
 for(const inside of [true,false]){
  let retries=0;const focusOpenedResult={current:false},button={},document={activeElement:button};
  const context=vm.createContext({focusOpenedResult,document,resultPanelRef:{current:{contains:element=>inside && element===button}},retryLookup:()=>retries++});
  vm.runInContext(method,context);context.retryResultLookup();assert.equal(retries,1);assert.equal(focusOpenedResult.current,inside);
 }
});

test('이력 결과 초점 예약은 결과 전환 시 취소한다',()=>{
 const source=readFileSync(new URL('../../gui/GeneratorHistory.jsx',import.meta.url),'utf8');
 const effect=source.slice(source.indexOf('  useEffect(()=>{\n    if(!focusOpenedResult.current'),source.indexOf('  useEffect(()=>{\n    cancelList();'));
 let cleanup,frame,cancelled=0,focused=0;const body={},document={body,activeElement:body};
 const context=vm.createContext({document,focusOpenedResult:{current:true},resultId:'job',resultLookup:{id:'job',loading:false},resultPanelRef:{current:{isConnected:true,focus:()=>focused++}},useEffect:fn=>cleanup=fn(),requestAnimationFrame:fn=>(frame=fn,7),cancelAnimationFrame:id=>{assert.equal(id,7);cancelled++;}});
 vm.runInContext(effect,context);assert.equal(typeof frame,'function');cleanup();assert.equal(cancelled,1);
 assert.equal(context.focusOpenedResult.current,true);
 vm.runInContext(effect,context);frame();assert.equal(focused,1);assert.equal(context.focusOpenedResult.current,false);
});

test('이력 밖 결과 영역도 결과 초점 이동 대상으로 연결된다',()=>{
 const source=readFileSync(new URL('../../gui/GeneratorHistory.jsx',import.meta.url),'utf8');
 for(const label of ['이력 밖 선택 결과','이력 범위 밖 선택 결과']){
  assert.ok(source.includes(`ref={resultPanelRef} tabIndex={-1} className="history-action-detail" aria-label="${label}"`));
 }
 const effect=source.slice(source.indexOf('  useEffect(()=>{\n    if(!focusOpenedResult.current'),source.indexOf('  useEffect(()=>{\n    cancelList();'));
 let frame,focused=0;const body={},document={body,activeElement:body};
 const context=vm.createContext({document,focusOpenedResult:{current:true},resultId:'job',resultLookup:{id:'job',error:'찾지 못했습니다'},resultPanelRef:{current:{isConnected:true,focus:()=>focused++}},useEffect:fn=>fn(),requestAnimationFrame:fn=>(frame=fn,1),cancelAnimationFrame:()=>{}});
 vm.runInContext(effect,context);frame();assert.equal(focused,1);
});

test('이력 입력을 읽는 동안 이동한 초점을 유지한다',async()=>{
 const source=readFileSync(new URL('../../gui/GeneratorHistory.jsx',import.meta.url),'utf8');
 const method=source.slice(source.indexOf('  async function showInput(id)'),source.indexOf('  return <details ref={detailsRef}'));
 for(const moved of [false,true]){
  let frame,focused=0;const body={},button={},other={},document={body,activeElement:button};
  const context=vm.createContext({document,read:async()=>({id:'job',request:{}}),setJob:()=>{},requestAnimationFrame:fn=>frame=fn,inputReviewRef:{current:{focus:()=>focused++}}});
  vm.runInContext(method,context);await context.showInput('job');document.activeElement=moved?other:body;frame();assert.equal(focused,moved?0:1);
 }
});

test('기존 이력 조회 인자는 유지하고 신호 지원 조회에만 신호를 전달한다',async()=>{
  const source=readFileSync(new URL('../../gui/GeneratorHistory.jsx',import.meta.url),'utf8');
  const method='async function read(id) {'+source.split('async function read(id) {')[1].split('\n  async function showResult',1)[0];
  const scope={service:'service',resultId:'',externalResultId:''};let mode='';
  const context=vm.createContext({AbortController,setTimeout:()=>1,clearTimeout:()=>{},untilAborted:promise=>promise,
    inputScope:{current:scope},inputRequest:{current:null},service:'service',statusCommand:'status',
    readJob:async(...args)=>{assert.equal(args.length,1);mode='legacy';return {id:args[0],request:{}};},readJobWithSignal:null});
  vm.runInContext(method,context);assert.equal((await context.read('job')).id,'job');assert.equal(mode,'legacy');
  context.readJobWithSignal=async(id,options)=>{assert.ok(options.signal instanceof AbortSignal);mode='signal';return {id,request:{}};};
  assert.equal((await context.read('job')).id,'job');assert.equal(mode,'signal');
});

test('이력 입력이 객체가 아니면 복원 대상에서 제외한다',async()=>{
 const source=readFileSync(new URL('../../gui/GeneratorHistory.jsx',import.meta.url),'utf8');
 const method='async function read(id) {'+source.split('async function read(id) {')[1].split('\n  async function showResult',1)[0];
 for(const request of [[], 'invalid', 42]){
  const scope={service:'service',resultId:'',externalResultId:''};
  const context=vm.createContext({AbortController,setTimeout:()=>1,clearTimeout:()=>{},untilAborted:promise=>promise,inputScope:{current:scope},inputRequest:{current:null},service:'service',statusCommand:'status',readJob:async()=>({id:'job',request}),readJobWithSignal:null});
  vm.runInContext(method,context);await assert.rejects(context.read('job'),/작업 입력을 확인할 수 없습니다/);
 }
});

test('취소 후 늦게 끝난 이력 입력은 반환하지 않는다',async()=>{
  const source=readFileSync(new URL('../../gui/GeneratorHistory.jsx',import.meta.url),'utf8');
  const read='async function read(id) {'+source.split('async function read(id) {')[1].split('\n  async function showResult',1)[0];
  const cancel='function cancelInput(){'+source.split('function cancelInput(){')[1].split('\n  function cancelList',1)[0];
  const scope={service:'service',resultId:'',externalResultId:''};let resolveLate,receivedSignal;
  const context=vm.createContext({AbortController,setTimeout:()=>1,clearTimeout:()=>{},untilAborted,
    inputScope:{current:scope},inputRequest:{current:null},service:'service',statusCommand:'status',readJob:null,
    readJobWithSignal:(_id,{signal})=>{receivedSignal=signal;return new Promise(resolve=>resolveLate=resolve);}});
  vm.runInContext(cancel+'\n'+read,context);
  const pending=context.read('job');context.cancelInput();assert.equal(receivedSignal.aborted,true);
  assert.equal(await pending,null);resolveLate({id:'job',request:{}});await Promise.resolve();assert.equal(context.inputRequest.current,null);
});
