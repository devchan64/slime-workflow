import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import vm from 'node:vm';

test('초안 검증 중 중복 편집과 저장을 보내지 않는다',async()=>{
  const source=readFileSync(new URL('../../gui/MapReview.jsx',import.meta.url),'utf8');
  const code=source.slice(source.indexOf('  async function applyDraft(next,action,stroke=null)'),source.indexOf('  async function inspectSaveRevision('));
  let resolve,calls=0,applied=null;const readRequest={current:null},savingRef={current:false},importRequest={current:null};
  const context=vm.createContext({window:{},readRequest,savingRef,importRequest,cellDirty:false,preview:{token:'t'},mapDraftSaveReason:()=>'',cell:null,draft:{cells:[]},past:[],future:[],
    setReading:()=>{},setPreview:()=>{},setFeedback:()=>{},setPast:()=>{},setFuture:()=>{},setCell:()=>{},setCellOriginal:()=>{},setStorageFailed:()=>{},setDraft:value=>applied=value,
    requestErrorMessage:error=>error.message,validMapDraftPreview:()=>true,applyMapPreview:async()=>{},
    readMap:()=>{calls++;readRequest.current={};return new Promise(done=>resolve=value=>{readRequest.current=null;done(value);});}});
  vm.runInContext(code,context);const first=context.applyDraft({cells:[],marker:'first'},'edit');
  await context.applyDraft({cells:[],marker:'second'},'edit');await context.save();assert.equal(calls,1);
  resolve({render:{},cells:0,reachable:0});await first;assert.equal(applied.marker,'first');
  importRequest.current={};await context.applyDraft({cells:[]},'edit');await context.save();assert.equal(calls,1);
});

test('브러시 검증 실패 안내는 이후 성공해도 유지된다',async()=>{
  const source=readFileSync(new URL('../../gui/MapReview.jsx',import.meta.url),'utf8');
  const code=source.slice(source.indexOf('  async function applyDraft(next,action,stroke=null)'),source.indexOf('  async function save(event)'));
  const failure=source.slice(source.indexOf('export function mapBrushFailure('),source.indexOf('\nexport function MapBrushErrors')).replace('export function','function');
  let brushErrors=[],feedback='',fail=true;
  const context=vm.createContext({window:{},readRequest:{current:null},savingRef:{current:false},importRequest:{current:null},cellDirty:false,cell:null,draft:{cells:[]},past:[],future:[],
    setReading:()=>{},setPreview:()=>{},setFeedback:value=>feedback=value,setBrushErrors:update=>brushErrors=update(brushErrors),setPast:()=>{},setFuture:()=>{},setCell:()=>{},setCellOriginal:()=>{},setStorageFailed:()=>{},setDraft:()=>{},
    requestErrorMessage:error=>error.message,validMapDraftPreview:()=>true,applyMapPreview:async()=>{},readMap:async()=>{if(fail)throw Error('연결 실패');return {render:{},cells:1,reachable:1};}});
  vm.runInContext(failure+'\n'+code,context);await context.applyDraft({cells:[]},'brush',[{column:1,row:2},{column:2,row:8,object:'tree'},{column:3,row:4}]);
  await context.applyDraft({cells:[]},'brush',[{column:5,row:6}]);assert.equal(brushErrors.length,2);assert.match(brushErrors[0].summary,/시작 열 1 · 행 2 · 끝 열 3 · 행 4 · 3곳 · 연결 실패/);assert.equal(brushErrors[0].points[1].position,'열 2 · 행 8');assert.equal(brushErrors[0].points[1].object,'tree');assert.match(brushErrors[1].summary,/열 5 · 행 6 · 1곳 · 연결 실패/);
  fail=false;await context.applyDraft({cells:[]},'brush');assert.match(feedback,/검증 완료/);assert.equal(brushErrors.length,2);
});

test('지도 처리 중 원본 복원·리비전·셀 조회를 시작하지 않는다',async()=>{
  const source=readFileSync(new URL('../../gui/MapReview.jsx',import.meta.url),'utf8');
  const parts=[['discardDraft','  async function discardDraft(){','  function discardRecovery()'],['inspectSaveRevision','  async function inspectSaveRevision(event){','  async function inspectCell('],['inspectCell','  async function inspectCell(','  const [ready,']];
  for(const blocked of ['read','import','save'])for(const [name,start,end] of parts){
    let called=0;const context=vm.createContext({readRequest:{current:blocked==='read'?{}:null},importRequest:{current:blocked==='import'?{}:null},savingRef:{current:blocked==='save'},draft:{map:'map'},window:{confirm:()=>{called++;return true;}},setReading:()=>called++,readMap:()=>{called++;}});
    vm.runInContext(source.slice(source.indexOf(start),source.indexOf(end)),context);await context[name]();assert.equal(called,0,`${name} · ${blocked}`);
  }
});

test('처리 중 브러시 입력은 대기열에서 꺼내지 않는다',()=>{
  const source=readFileSync(new URL('../../gui/MapReview.jsx',import.meta.url),'utf8');
  const start=source.indexOf('  useEffect(()=>{\n    const queue=window.mapReviewBrushQueue;'),end=source.indexOf('  const destination=',start);
  for(const blocked of ['read','import','save']){
    const queue=[[{column:0,row:0}]];
    const context=vm.createContext({window:{mapReviewBrushQueue:queue},reading:false,cellDirty:false,draft:{},strokeCount:0,readRequest:{current:blocked==='read'?{}:null},importRequest:{current:blocked==='import'?{}:null},savingRef:{current:blocked==='save'},useEffect:fn=>fn()});
    vm.runInContext(source.slice(start,end),context);assert.equal(queue.length,1,blocked);
  }
});

test('대기 중인 브러시 입력은 저장과 초안 폐기보다 먼저 처리한다',async()=>{
  const source=readFileSync(new URL('../../gui/MapReview.jsx',import.meta.url),'utf8');
  const save=source.slice(source.indexOf('  async function save(event){'),source.indexOf('  async function inspectSaveRevision('));
  const discard=source.slice(source.indexOf('  async function discardDraft(){'),source.indexOf('  function discardRecovery()'));
  for(const blocked of ['active','busy','queued']){
    let feedback='',calls=0;const context=vm.createContext({window:{mapReviewBrushActive:blocked==='active',mapReviewBrushBusy:blocked==='busy',mapReviewBrushQueue:blocked==='queued'?[[]]:[],confirm:()=>{calls++;return true;}},readRequest:{current:null},importRequest:{current:null},savingRef:{current:false},preview:{token:'t'},mapDraftSaveReason:()=>'',setFeedback:value=>feedback=value});
    vm.runInContext(save+'\n'+discard,context);await context.save();assert.match(feedback,/브러시 편집/);feedback='';await context.discardDraft();assert.match(feedback,/브러시 편집/);assert.equal(calls,0);
  }
});

test('대기 획은 다른 편집과 가져오기보다 먼저 처리하고 셀 수정 중에는 보존한다',async()=>{
  const source=readFileSync(new URL('../../gui/MapReview.jsx',import.meta.url),'utf8');
  const apply=source.slice(source.indexOf('  async function applyDraft(next,action,stroke=null)'),source.indexOf('  async function save(event)'));
  const load=source.slice(source.indexOf('  async function importDraft(file,focused=false)'),source.indexOf('  async function discardDraft()'));
  const queue=[[{tool:'raise',column:0,row:0}]];let feedback='',error='',reads=0;
  const context=vm.createContext({window:{mapReviewBrushBusy:true,mapReviewBrushQueue:queue},readRequest:{current:null},importRequest:{current:null},savingRef:{current:false},setFeedback:value=>feedback=value,setImportError:value=>error=value});
  vm.runInContext(apply+'\n'+load,context);await context.applyDraft({},'edit');await context.importDraft({text:()=>reads++});
  assert.match(feedback,/브러시/);assert.match(error,/브러시/);assert.equal(reads,0);assert.equal(queue.length,1);
  const start=source.indexOf('  useEffect(()=>{\n    const queue=window.mapReviewBrushQueue;'),end=source.indexOf('  const destination=',start);
  Object.assign(context,{reading:false,cellDirty:true,draft:{},strokeCount:0,useEffect:fn=>fn()});
  vm.runInContext(source.slice(start,end),context);assert.equal(queue.length,1);
});

test('처리되지 않은 브러시 획은 화면 이동과 새로고침에서 보호한다',()=>{
  const source=readFileSync(new URL('../../gui/MapReview.jsx',import.meta.url),'utf8');
  const start=source.indexOf('  useEffect(()=>{\n    const warn=event=>'),end=source.indexOf('  const atCell=',start);
  const navigation=source.slice(source.indexOf('  function guardNavigation(event){'),source.indexOf('  return <article className="map-review">'));
  for(const state of ['active','busy','queued','idle']){
    let warn,feedback='',prevented=0;
    const context=vm.createContext({field:true,cellDirty:false,unsafeAutosave:false,saving:false,saveUncertain:false,
      window:{mapReviewBrushActive:state==='active',mapReviewBrushBusy:state==='busy',mapReviewBrushQueue:state==='queued'?[[]]:[],addEventListener:(_,fn)=>warn=fn,removeEventListener:()=>{}},
      useEffect:fn=>fn(),setFeedback:value=>feedback=value});
    vm.runInContext(source.slice(start,end)+'\n'+navigation,context);
    const unload={preventDefault:()=>prevented++};warn(unload);
    const event={button:0,preventDefault:()=>prevented++};context.guardNavigation(event);
    assert.equal(prevented,state==='idle'?0:2,state);
    if(state!=='idle'){assert.equal(unload.returnValue,true);assert.match(feedback,/브러시/);}
  }
});
