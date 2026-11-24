import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import vm from 'node:vm';
import {untilAborted} from '../../gui/managementCommand.js';

test('변경 요청이 지연되면 결과 확인을 안내하고 늦은 응답은 무시한다',async()=>{
 const source=readFileSync(new URL('../../gui/WorkflowResults.jsx',import.meta.url),'utf8');
 const fn=source.slice(source.indexOf('async function workflowMutation'),source.indexOf('function MediaPreview'));
 let timer,resolve;
 const context=vm.createContext({AbortController,untilAborted,setTimeout:fn=>(timer=fn,1),clearTimeout:()=>{}});
 vm.runInContext(fn,context);
 const pending=context.workflowMutation(()=>new Promise(done=>resolve=done),'workflow-cancel',{});
 timer();await assert.rejects(pending,/처리 여부.*결과를 갱신/);resolve({ok:true});
});

test('워크플로우 미리보기와 Kimodo 조회는 시간 초과 후 대기를 해제하고 늦은 응답을 무시한다',async()=>{
 const source=readFileSync(new URL('../../gui/WorkflowResults.jsx',import.meta.url),'utf8');
 for(const [start,end] of [['function MediaPreview','function KimodoMotion'],['function KimodoMotion','export default function WorkflowResults']]){
  const part=source.slice(source.indexOf(start),source.indexOf(end));
  const fn=part.slice(part.indexOf('  async function load()'),part.indexOf('  return <'));
  let timer,resolve,error='',busy=false,updates=0;
  const delayed=()=>new Promise(done=>resolve=done);
  const context=vm.createContext({AbortController,untilAborted,pending:{current:null},setTimeout:fn=>(timer=fn,1),clearTimeout:()=>{},
   buttonRef:{current:{}},retryRef:{current:{}},document:{activeElement:{}},setBusy:value=>busy=value,setError:value=>error=value,setSource:()=>updates++,setVideo:()=>updates++,
   call:delayed,managementCommand:delayed,audio:false,result:{step_id:'step',job_id:'job',outputs:{}},session:'session',run:'run'});
  vm.runInContext(fn,context);const waiting=context.load();assert.equal(busy,true);
  timer();await waiting;assert.equal(busy,false);assert.match(error,/시간이 초과/);
  resolve({preview_png:'data'});await new Promise(done=>setImmediate(done));assert.equal(updates,0);
 }
});

test('미리보기 화면 종료 시 진행 중인 조회를 중단하고 늦은 결과를 적용하지 않는다',async()=>{
 const source=readFileSync(new URL('../../gui/WorkflowResults.jsx',import.meta.url),'utf8');
 for(const [start,end] of [['function MediaPreview','function KimodoMotion'],['function KimodoMotion','export default function WorkflowResults']]){
  const part=source.slice(source.indexOf(start),source.indexOf(end));
  const fn=part.slice(part.indexOf('  async function load()'),part.indexOf('  return <'));
  const cleanup=part.match(/useEffect\(\(\)=>\(\)=>\{pending\.current\?\.abort\(\);pending\.current=null;\},\[\]\);/)[0];
  let resolve,stop,updates=0,errors=0,busyChanges=0;
  const delayed=()=>new Promise(done=>resolve=done);
  const context=vm.createContext({AbortController,untilAborted,pending:{current:null},useEffect:fn=>stop=fn(),setTimeout:()=>1,clearTimeout:()=>{},
   buttonRef:{current:{}},retryRef:{current:{}},document:{activeElement:{}},setBusy:()=>busyChanges++,setError:()=>errors++,setSource:()=>updates++,setVideo:()=>updates++,
   call:delayed,managementCommand:delayed,audio:false,result:{step_id:'step',job_id:'job',outputs:{}},session:'session',run:'run'});
  vm.runInContext(fn,context);vm.runInContext(cleanup,context);const waiting=context.load();const controller=context.pending.current;
  stop();await waiting;resolve({preview_png:'YWJj'});await new Promise(done=>setImmediate(done));
  assert.equal(controller.signal.aborted,true);assert.equal(updates,0);assert.equal(busyChanges,1);assert.equal(errors,1);
 }
});

test('미리보기 응답은 이미지와 오디오 데이터가 올바를 때만 열린다',async()=>{
 const source=readFileSync(new URL('../../gui/WorkflowResults.jsx',import.meta.url),'utf8');
 const part=source.slice(source.indexOf('function MediaPreview'),source.indexOf('function KimodoMotion'));
 const fn=part.slice(part.indexOf('  async function load()'),part.indexOf('  return <'));
 for(const audio of [false,true])for(const valid of [false,true]){
  let shown='',error='',busy=false;
  const data={[audio?'wav':'preview_png']:valid?'YWJj':'not base64'};
  const context=vm.createContext({AbortController,untilAborted,pending:{current:null},setTimeout:()=>1,clearTimeout:()=>{},
   buttonRef:{current:{}},retryRef:{current:{}},document:{activeElement:{}},setBusy:value=>busy=value,setError:value=>error=value,setSource:value=>shown=value,
   call:async()=>data,audio,result:{step_id:'step'},session:'session',run:'run'});
  vm.runInContext(fn,context);await context.load();assert.equal(busy,false);
  if(valid){assert.match(shown,audio?/^data:audio\/wav;base64,/:/^data:image\/png;base64,/);assert.equal(error,'');}
  else{assert.equal(shown,'');assert.match(error,/형식/);}
 }
});

test('이전 워크플로우 이미지와 오디오 요소의 오류는 현재 미리보기에 반영하지 않는다',()=>{
 const source=readFileSync(new URL('../../gui/WorkflowResults.jsx',import.meta.url),'utf8');
 const part=source.slice(source.indexOf('function MediaPreview'),source.indexOf('function KimodoMotion'));
 const handlers=part.split('onError={event=>{').slice(1).map(item=>item.split('}}/>')[0]);
 assert.equal(handlers.length,2);
 for(const body of handlers){
  const current={};let error='';const context=vm.createContext({mediaRef:{current},restoreMediaFocus:{current:false},document:{activeElement:current},setError:value=>error=value});
  vm.runInContext(`function fail(event){${body}}`,context);context.fail({currentTarget:{}});assert.equal(error,'');
  context.fail({currentTarget:current});assert.match(error,/미리보기/);assert.equal(context.restoreMediaFocus.current,true);
 }
});

test('미리보기 오류로 사라진 초점만 재시도 버튼으로 돌린다',()=>{
 const source=readFileSync(new URL('../../gui/WorkflowResults.jsx',import.meta.url),'utf8');
 const effect=source.match(/useEffect\(\(\)=>\{if\(error && restoreMediaFocus\.current\).*?\},\[error\]\);/)[0];
 for(const moved of [true,false]){
  const body={},other={};let focused=false;
  const context=vm.createContext({useEffect:fn=>fn(),error:'오류',restoreMediaFocus:{current:true},document:{body,activeElement:moved?other:body},retryRef:{current:{focus:()=>focused=true}}});
  vm.runInContext(effect,context);assert.equal(focused,!moved);assert.equal(context.restoreMediaFocus.current,false);
 }
});

test('미리보기 재조회가 끝나면 사라진 초점을 열기 버튼으로 복구한다',async()=>{
 const source=readFileSync(new URL('../../gui/WorkflowResults.jsx',import.meta.url),'utf8');
 const part=source.slice(source.indexOf('function MediaPreview'),source.indexOf('function KimodoMotion'));
 const fn=part.slice(part.indexOf('  async function load()'),part.indexOf('  return <'));
 const body={},retry={},button={disabled:false};let focused=false,scheduled;
 button.focus=()=>focused=true;
 const doc={body,activeElement:retry};
 const context=vm.createContext({AbortController,untilAborted,pending:{current:null},setTimeout:()=>1,clearTimeout:()=>{},requestAnimationFrame:fn=>scheduled=fn,
  buttonRef:{current:button},retryRef:{current:retry},document:doc,setBusy:()=>{},setError:()=>{},setSource:()=>{},call:async()=>({preview_png:'YWJj'}),
  audio:false,result:{step_id:'step'},session:'session',run:'run'});
 vm.runInContext(fn,context);await context.load();doc.activeElement=body;scheduled();assert.equal(focused,true);
});

test('워크플로우 결과 조회는 시간 초과 후 갱신할 수 있고 종료 후 늦은 응답을 무시한다',async()=>{
 const source=readFileSync(new URL('../../gui/WorkflowResults.jsx',import.meta.url),'utf8');
 const start=source.indexOf('  useEffect(() => {\n    let active = true,timedOut=false;');
 const effect=source.slice(start,source.indexOf('  }, [session,run,call,revision]);',start)+'  }, [session,run,call,revision]);'.length);
 for(const finish of ['timeout','close']){
  let timer,cleanup,resolve,error='',busy=false,updates=0;
  const context=vm.createContext({AbortController,untilAborted,session:'s',run:'r',revision:0,viewPending:{current:false},requiresRefresh:{current:false},useEffect:fn=>cleanup=fn(),
   setTimeout:fn=>(timer=fn,1),clearTimeout:()=>{},call:()=>new Promise(done=>resolve=done),setBusy:value=>busy=value,setError:value=>error=value,
   setView:()=>updates++,setObservation:()=>{},restoreRefreshFocus:{current:false},Date});
  vm.runInContext(effect,context);assert.equal(busy,true);
  if(finish==='timeout')timer();else cleanup();
  await new Promise(done=>setImmediate(done));resolve({run_id:'r'});await new Promise(done=>setImmediate(done));
  assert.equal(updates,0);
  if(finish==='timeout'){assert.equal(busy,false);assert.match(error,/시간이 초과/);}else assert.equal(error,'');
 }
});

test('워크플로우 결과는 시간 초과 뒤 정상 재조회로 오류와 대기를 해제한다',async()=>{
 const source=readFileSync(new URL('../../gui/WorkflowResults.jsx',import.meta.url),'utf8');
 const start=source.indexOf('  useEffect(() => {\n    let active = true,timedOut=false;');
 const marker='  }, [session,run,call,revision]);',effect=source.slice(start,source.indexOf(marker,start)+marker.length);
 let timer,error='',busy=false,view=null,first=true;
 const expected={run_id:'r',steps:[],results:[],choices:[],retries:[]};
 const context=vm.createContext({AbortController,untilAborted,session:'s',run:'r',revision:0,viewPending:{current:false},requiresRefresh:{current:false},useEffect:fn=>fn(),
  setTimeout:fn=>(timer=fn,1),clearTimeout:()=>{},call:()=>first?new Promise(()=>{}):Promise.resolve(expected),
  setBusy:value=>busy=value,setError:value=>error=value,setView:value=>view=value,setObservation:()=>{},
  validWorkflowView:value=>value===expected,restoreRefreshFocus:{current:false},Date});
 vm.runInContext(effect,context);timer();await new Promise(done=>setImmediate(done));assert.match(error,/시간이 초과/);assert.equal(busy,false);
 first=false;vm.runInContext(effect,context);await new Promise(done=>setImmediate(done));
 assert.equal(error,'');assert.equal(busy,false);assert.equal(view,expected);assert.equal(context.requiresRefresh.current,false);
});

test('생성기 목록은 시간 초과와 손상 응답을 따로 알리고 정상 목록을 적용한다',async()=>{
 const source=readFileSync(new URL('../../gui/WorkflowResults.jsx',import.meta.url),'utf8');
 const start=source.indexOf('  useEffect(()=>{\n    let active=true,timedOut=false;const controller=');
 const end=source.indexOf('  },[call,catalogRevision]);',start)+'  },[call,catalogRevision]);'.length;
 const effect=source.slice(start,end);
 for(const outcome of ['timeout','invalid','valid']){
  let timer,error='',catalog=null;
  const payload=outcome==='valid'?{generators:{kimodo:{label:'Kimodo',inputs:{prompt:{type:'text'}}}}}:{generators:{kimodo:{label:'Kimodo',inputs:{prompt:null}}}};
  const context=vm.createContext({AbortController,untilAborted,useEffect:fn=>fn(),call:()=>outcome==='timeout'?new Promise(()=>{}):Promise.resolve(payload),
   setTimeout:fn=>(timer=fn,1),clearTimeout:()=>{},setCatalogError:value=>error=value,setCatalog:value=>catalog=value,setCatalogLoading:()=>{},setCatalogReady:()=>{},catalogRevision:0});
  vm.runInContext(effect,context);if(outcome==='timeout')timer();await new Promise(done=>setImmediate(done));
  if(outcome==='valid'){assert.equal(error,'');assert.equal(catalog,payload.generators);}
  else{assert.equal(catalog,null);assert.match(error,outcome==='timeout'?/시간이 초과/:/형식/);}
 }
});

test('생성기 목록 재조회 후 사라진 초점만 결과 안내로 돌린다',()=>{
 const source=readFileSync(new URL('../../gui/WorkflowResults.jsx',import.meta.url),'utf8');
 const effect=source.match(/useEffect\(\(\)=>\{if\(!catalogLoading && restoreCatalogFocus\.current\).*?\},\[catalogLoading,catalogError\]\);/)[0];
 for(const error of ['', '오류'])for(const moved of [true,false]){
  const body={},other={};let focused='';
  const context=vm.createContext({useEffect:fn=>fn(),catalogLoading:false,catalogError:error,restoreCatalogFocus:{current:true},document:{body,activeElement:moved?other:body},
   catalogRetryRef:{current:{focus:()=>focused='retry'}},catalogStatusRef:{current:{focus:()=>focused='status'}}});
  vm.runInContext(effect,context);assert.equal(focused,moved?'':error?'retry':'status');
 }
});

test('실행 취소 검토는 열 때 초점을 받고 유지 선택 후 복귀한다',()=>{
 const source=readFileSync(new URL('../../gui/WorkflowResults.jsx',import.meta.url),'utf8');
 const effect=source.match(/useEffect\(\(\)=>\{if\(confirmCancel\).*?\},\[confirmCancel\]\);/)[0];
 for(const open of [true,false])for(const moved of [true,false]){
  let focused='';const body={},other={};
  const context=vm.createContext({useEffect:fn=>fn(),confirmCancel:open,restoreCancelFocus:{current:true},document:{body,activeElement:moved?other:body},
   cancelReviewRef:{current:{focus:()=>focused='review'}},cancelTriggerRef:{current:{focus:()=>focused='trigger'}}});
  vm.runInContext(effect,context);assert.equal(focused,open?'review':moved?'':'trigger');
 }
});

test('변경 요청 중에는 예약된 결과 자동 갱신이 실행되지 않는다',()=>{
 const source=readFileSync(new URL('../../gui/WorkflowResults.jsx',import.meta.url),'utf8');
 const start=source.indexOf('  useEffect(() => {\n    if (busy || error || confirmCancel');
 const marker='  }, [view,busy,error,confirmCancel]);',effect=source.slice(start,source.indexOf(marker,start)+marker.length);
 let timer,revision=0;const pending={current:false};
 const context=vm.createContext({useEffect:fn=>fn(),busy:false,error:'',confirmCancel:false,view:{steps:[{state:'waiting'}]},
  setTimeout:fn=>(timer=fn,1),clearTimeout:()=>{},mutationPending:pending,viewPending:{current:false},setBusy:()=>{},setRevision:fn=>revision=fn(revision)});
 vm.runInContext(effect,context);pending.current=true;timer();assert.equal(revision,0);
 pending.current=false;timer();assert.equal(revision,1);
});
