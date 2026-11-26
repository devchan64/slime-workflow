import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import vm from 'node:vm';
import {untilAborted} from '../../gui/managementCommand.js';
import {requestErrorMessage} from '../../gui/requestError.mjs';
import {restoreLostFocus,visibleFocusTarget} from '../../gui/restoreLostFocus.mjs';

test('DWPose 검토 실패는 사라진 초점만 복구한다',()=>{
 const source=readFileSync(new URL('../../gui/DwposePage.jsx',import.meta.url),'utf8');
 const effect=source.match(/useEffect\(\(\)=>\{if\(busy \|\| pending \|\| !notice \|\| !focusOnReview\.current\).*?\},\[busy,pending,notice\]\);/s)?.[0];assert.ok(effect);
 for(const moved of [false,true]){
  let run,frame,focused=0;const body={},button={isConnected:true,focus:()=>focused++},document={body,activeElement:moved?{}:body},focusOnReview={current:true};
  const context=vm.createContext({busy:false,pending:null,notice:'오류',focusOnReview,reviewButtonRef:{current:button},document,restoreLostFocus,visibleFocusTarget:value=>value,useEffect:fn=>run=fn,requestAnimationFrame:fn=>(frame=fn,1),cancelAnimationFrame:()=>{}});
  vm.runInContext(effect,context);run();frame();assert.equal(focused,moved?0:1);assert.equal(focusOnReview.current,false);
 }
});

test('DWPose 검토 지연은 중복을 막고 시간 초과 뒤 재시도한다',async()=>{
 const source=readFileSync(new URL('../../gui/DwposePage.jsx',import.meta.url),'utf8');
 const code=source.slice(source.indexOf('  async function review()'),source.indexOf('  async function submit()',source.indexOf('  async function review()')));
 for(const stage of ['image','handoff']){
  let timeout,busy=false,notice='',pending=null,calls=0,slow=true;const reviewRequest={current:null};
  const file={};const context=vm.createContext({AbortController,untilAborted,requestErrorMessage,reviewRequest,reviewFileName:{current:""},focusOnReview:{current:false},reviewButtonRef:{current:null},document:{activeElement:null},inputRef:{current:{file,hands:false,face:false}},imageSelectionRevision:{current:0},imageChecking:{current:false},reviewEpoch:{current:0},file,hands:false,face:false,setTimeout:fn=>(timeout=fn,1),clearTimeout:()=>{},setBusy:v=>busy=v,setNotice:v=>notice=v,setPending:v=>pending=v,pngData:()=>slow && stage==='image'?new Promise(()=>{}):Promise.resolve('png'),handoff:{clearReview:()=>{},preview:()=>{calls++;return slow && stage==='handoff'?new Promise(()=>{}):Promise.resolve();}}});
  vm.runInContext(code,context);const first=context.review();await context.review();await new Promise(resolve=>setImmediate(resolve));timeout();await first;assert.match(notice,/초과/);assert.equal(busy,false);assert.equal(pending,null);assert.equal(reviewRequest.current,null);assert.equal(calls,stage==='handoff'?1:0);
  slow=false;await context.review();assert.equal(notice,'');assert.equal(busy,false);assert.equal(pending.images[0],'png');
 }
});

test('DWPose 이미지 확인 중 입력이 바뀌면 GPU 상태 조회를 시작하지 않는다',async()=>{
 const source=readFileSync(new URL('../../gui/DwposePage.jsx',import.meta.url),'utf8');
 const code=source.slice(source.indexOf('  async function review()'),source.indexOf('  async function submit()',source.indexOf('  async function review()')));
 let resolve,notice='',calls=0;const file={},inputRef={current:{file,hands:false,face:false}},reviewRequest={current:null};
 const context=vm.createContext({AbortController,untilAborted,requestErrorMessage,reviewRequest,reviewFileName:{current:""},focusOnReview:{current:false},reviewButtonRef:{current:null},document:{activeElement:null},inputRef,imageSelectionRevision:{current:0},imageChecking:{current:false},reviewEpoch:{current:0},file,hands:false,face:false,setTimeout:()=>1,clearTimeout:()=>{},setBusy:()=>{},setNotice:v=>notice=v,setPending:()=>{},pngData:()=>new Promise(done=>resolve=done),handoff:{preview:()=>calls++}});
 vm.runInContext(code,context);const pending=context.review();inputRef.current={file,hands:true,face:false};resolve('png');await pending;assert.equal(calls,0);assert.match(notice,/입력이 변경/);
});

test('DWPose 검토는 렌더 전 갱신된 최신 입력을 사용한다',async()=>{
 const source=readFileSync(new URL('../../gui/DwposePage.jsx',import.meta.url),'utf8');
 const code=source.slice(source.indexOf('  async function review()'),source.indexOf('  async function submit()',source.indexOf('  async function review()')));
 const oldFile={name:'old.png'},newFile={name:'new.png'},inputRef={current:{file:newFile,hands:true,face:false}},reviewFileName={current:''};let observed=null,pending=null;
 const context=vm.createContext({AbortController,untilAborted,requestErrorMessage,reviewRequest:{current:null},reviewFileName,focusOnReview:{current:false},reviewButtonRef:{current:null},document:{activeElement:null},inputRef,imageSelectionRevision:{current:1},imageChecking:{current:false},reviewEpoch:{current:0},file:oldFile,hands:false,face:false,setTimeout:()=>1,clearTimeout:()=>{},setBusy:()=>{},setNotice:()=>{},setPending:value=>pending=value,pngData:value=>{observed=value;return Promise.resolve('png');},handoff:{preview:()=>Promise.resolve(),clearReview:()=>{}}});
 vm.runInContext(code,context);await context.review();assert.equal(observed,newFile);assert.equal(reviewFileName.current,'new.png');assert.equal(pending.pose_include_hands,true);
});

test('DWPose 이미지 제거 직후 검토하면 선택 안내를 표시한다',async()=>{
 const source=readFileSync(new URL('../../gui/DwposePage.jsx',import.meta.url),'utf8');
 const code=source.slice(source.indexOf('  async function review()'),source.indexOf('  async function submit()',source.indexOf('  async function review()')));
 let notice='',calls=0;const context=vm.createContext({reviewRequest:{current:null},reviewFileName:{current:''},focusOnReview:{current:false},reviewButtonRef:{current:null},document:{activeElement:null},inputRef:{current:{file:null,hands:false,face:false}},imageSelectionRevision:{current:1},imageChecking:{current:false},setNotice:value=>notice=value,pngData:()=>calls++});
 vm.runInContext(code,context);await context.review();assert.match(notice,/PNG를 선택/);assert.equal(calls,0);
});

test('DWPose 검토 취소는 검토 영역에서 잃은 초점만 복구한다',()=>{
 const source=readFileSync(new URL('../../gui/DwposePage.jsx',import.meta.url),'utf8');
 const code=source.slice(source.indexOf('  function closeReview()'),source.indexOf('  function cleaned(',source.indexOf('  function closeReview()')));
 for(const scenario of ['lost','moved','outside','new-review']){
  let frame,focused=0;const body={},inside={},other={},document={body,activeElement:scenario==='outside'?other:inside},reviewEpoch={current:0};
  const context=vm.createContext({document,restoreLostFocus,visibleFocusTarget,reviewEpoch,reviewRequest:{current:null},reviewRef:{current:{contains:value=>value===inside}},reviewButtonRef:{current:{isConnected:true,focus:()=>focused++}},focusFrame:{current:null},setPending:()=>{},handoff:{clearReview:()=>{}},cancelAnimationFrame:()=>{},requestAnimationFrame:fn=>(frame=fn,1)});
  vm.runInContext(code,context);context.closeReview();document.activeElement=['lost','new-review'].includes(scenario)?body:other;if(scenario==='new-review')reviewEpoch.current++;frame?.();assert.equal(focused,scenario==='lost'?1:0,scenario);
 }
});

test('DWPose 검토가 열릴 때 사라진 초점만 옮긴다',()=>{
 const source=readFileSync(new URL('../../gui/DwposePage.jsx',import.meta.url),'utf8');
 const effect=source.match(/useEffect\(\(\)=>\{if\(!pending \|\| !focusOnReview\.current\).*?\},\[pending\]\);/s)?.[0];assert.ok(effect);
 for(const moved of [false,true]){
  let run,frame,focused=0,cancelled=0;const body={},other={},document={body,activeElement:moved?other:body};
  const context=vm.createContext({document,restoreLostFocus,pending:{},focusOnReview:{current:true},reviewRef:{current:{isConnected:true,focus:()=>focused++}},useEffect:fn=>run=fn,requestAnimationFrame:fn=>(frame=fn,1),cancelAnimationFrame:()=>cancelled++});
  vm.runInContext(effect,context);const cleanup=run();frame();cleanup();assert.equal(focused,moved?0:1);assert.equal(cancelled,1);
 }
});

test('DWPose 화면 종료 후 늦은 검토 응답은 상태를 변경하지 않는다',async()=>{
 const source=readFileSync(new URL('../../gui/DwposePage.jsx',import.meta.url),'utf8');
 const code=source.slice(source.indexOf('  async function review()'),source.indexOf('  async function submit()',source.indexOf('  async function review()')));
 let resolve,updates=0;const file={},reviewRequest={current:null};
 const context=vm.createContext({AbortController,untilAborted,requestErrorMessage,reviewRequest,reviewFileName:{current:""},focusOnReview:{current:false},reviewButtonRef:{current:null},document:{activeElement:null},inputRef:{current:{file,hands:false,face:false}},imageSelectionRevision:{current:0},imageChecking:{current:false},reviewEpoch:{current:0},file,hands:false,face:false,setTimeout:()=>1,clearTimeout:()=>{},setBusy:()=>updates++,setNotice:()=>updates++,setPending:()=>updates++,pngData:()=>Promise.resolve('png'),handoff:{clearReview:()=>{},preview:()=>new Promise(done=>resolve=done)}});
 vm.runInContext(code,context);const pending=context.review();await new Promise(done=>setImmediate(done));const controller=reviewRequest.current;reviewRequest.current=null;controller.abort();const before=updates;resolve();await pending;assert.equal(updates,before);
});

test('DWPose 이력 입력 본문 조회는 상위 중단 신호를 따른다',async()=>{
 const source=readFileSync(new URL('../../gui/DwposePage.jsx',import.meta.url),'utf8');
 const code=source.slice(source.indexOf('  async function readJob('),source.indexOf('  function restore(',source.indexOf('  async function readJob(')));
 const parent=new AbortController();let childSignal;
 const context=vm.createContext({AbortController,untilAborted,document:{activeElement:null},inputRef:{current:{}},imageSelectionRevision:{current:0},imageChecking:{current:false},reviewEpoch:{current:0},setTimeout:()=>1,clearTimeout:()=>{},fetch:(_url,options)=>{childSignal=options.signal;return Promise.resolve({ok:true,headers:{get:()=>"false"},blob:()=>new Promise(()=>{})});},File:class{}});
 vm.runInContext(code,context);const pending=context.readJob('job',{signal:parent.signal});await new Promise(done=>setImmediate(done));parent.abort();await assert.rejects(pending,error=>error.name==='AbortError');assert.equal(childSignal.aborted,true);
});

test('DWPose 이력 복원은 손상된 옵션이나 이미지를 거부한다',async()=>{
 const source=readFileSync(new URL('../../gui/DwposePage.jsx',import.meta.url),'utf8');
 const code=source.slice(source.indexOf('  async function readJob('),source.indexOf('  function restore(',source.indexOf('  async function readJob(')));
 for(const kind of ['header','image','valid']){
  const response={ok:true,headers:{get:name=>name==='X-Pose-Hands' && kind==='header'?null:'false'},blob:()=>Promise.resolve({})};
  const context=vm.createContext({AbortController,untilAborted,document:{activeElement:null},inputRef:{current:{}},imageSelectionRevision:{current:0},imageChecking:{current:false},reviewEpoch:{current:0},setTimeout:()=>1,clearTimeout:()=>{},fetch:()=>Promise.resolve(response),File:class{},pngData:()=>kind==='image'?Promise.reject(new Error('PNG 오류')):Promise.resolve('png')});
  vm.runInContext(code,context);if(kind==='valid'){const result=await context.readJob('job');assert.equal(result.request.pose_include_hands,false);}else await assert.rejects(context.readJob('job'),kind==='header'?/옵션/:/PNG/);
 }
});

test('DWPose 이력 PNG 확인이 지연되면 시간 초과 뒤 다시 조회할 수 있다',async()=>{
 const source=readFileSync(new URL('../../gui/DwposePage.jsx',import.meta.url),'utf8');
 const code=source.slice(source.indexOf('  async function readJob('),source.indexOf('  function restore(',source.indexOf('  async function readJob(')));
 let timeout,resolve,slow=true;const response={ok:true,headers:{get:()=>"true"},blob:()=>Promise.resolve({})};
 const context=vm.createContext({AbortController,untilAborted,document:{activeElement:null},inputRef:{current:{}},imageSelectionRevision:{current:0},imageChecking:{current:false},reviewEpoch:{current:0},setTimeout:fn=>(timeout=fn,1),clearTimeout:()=>{},fetch:()=>Promise.resolve(response),File:class{},pngData:()=>slow?new Promise(done=>resolve=done):Promise.resolve('png')});
 vm.runInContext(code,context);const pending=context.readJob('job');await new Promise(done=>setImmediate(done));timeout();await assert.rejects(pending,/시간이 초과/);resolve('png');slow=false;const result=await context.readJob('job');assert.equal(result.request.pose_include_hands,true);
});

test('DWPose 이력 복원은 이동한 초점과 새 검토를 방해하지 않는다',()=>{
 const source=readFileSync(new URL('../../gui/DwposePage.jsx',import.meta.url),'utf8');
 const code=source.slice(source.indexOf('  function restore('),source.indexOf('  async function review()',source.indexOf('  function restore(')));
 for(const scenario of ['lost','moved','review']){
  let frame,focused=0;const body={},origin={},other={},document={body,activeElement:origin},file={},inputRef={current:{file,hands:false,face:false}},reviewEpoch={current:0};
  const record={reviewAtStart:0,inputAtStart:inputRef.current,imageAtStart:0,checkingAtStart:false,focusAtStart:origin,file:{}};
  const context=vm.createContext({document,formRegion:{current:null},inputRef,reviewEpoch,reviewRequest:{current:null},interactionRef:{current:{busy:false,pending:null}},imageChecking:{current:false},imageSelectionRevision:{current:0},focusFrame:{current:null},handsRef:{current:{isConnected:true,focus:()=>focused++}},setFile:()=>{},setHands:()=>{},setFace:()=>{},setNotice:()=>{},cancelAnimationFrame:()=>{},requestAnimationFrame:fn=>(frame=fn,1)});
  vm.runInContext(code,context);context.restore({pose_include_hands:false,pose_include_face:false},record);document.activeElement=scenario==='moved'?other:body;if(scenario==='review')reviewEpoch.current++;frame();assert.equal(focused,scenario==='lost'?1:0,scenario);
 }
});

test('DWPose 이력 입력을 연속 적용하면 이전 조회가 첫 복원을 덮지 않는다',()=>{
 const source=readFileSync(new URL('../../gui/DwposePage.jsx',import.meta.url),'utf8');
 const code=source.slice(source.indexOf('  function restore('),source.indexOf('  async function review()',source.indexOf('  function restore(')));
 const file={},inputRef={current:{file,hands:false,face:false}},record={reviewAtStart:0,inputAtStart:inputRef.current,imageAtStart:0,checkingAtStart:false,focusAtStart:null,file:{}};
 let applied=0;const context=vm.createContext({document:{activeElement:null,body:{}},formRegion:{current:null},inputRef,reviewEpoch:{current:0},reviewRequest:{current:null},interactionRef:{current:{busy:false,pending:null}},imageChecking:{current:false},imageSelectionRevision:{current:0},focusFrame:{current:null},handsRef:{current:null},setFile:()=>applied++,setHands:()=>{},setFace:()=>{},setNotice:()=>{},cancelAnimationFrame:()=>{},requestAnimationFrame:()=>1});
 vm.runInContext(code,context);context.restore({pose_include_hands:true,pose_include_face:false},record);assert.throws(()=>context.restore({pose_include_hands:false,pose_include_face:false},record),/입력이 변경/);assert.equal(applied,1);
});

test('DWPose 검토 중 입력이 바뀌면 이전 검토를 표시하지 않는다',async()=>{
 const source=readFileSync(new URL('../../gui/DwposePage.jsx',import.meta.url),'utf8');
 const code=source.slice(source.indexOf('  async function review()'),source.indexOf('  async function submit()',source.indexOf('  async function review()')));
 let resolve,notice='',pending=null,cleared=0;const file={},inputRef={current:{file,hands:false,face:false}},reviewRequest={current:null};
 const context=vm.createContext({AbortController,untilAborted,requestErrorMessage,reviewRequest,reviewFileName:{current:""},focusOnReview:{current:false},reviewButtonRef:{current:null},document:{activeElement:null},inputRef,imageSelectionRevision:{current:0},imageChecking:{current:false},reviewEpoch:{current:0},file,hands:false,face:false,setTimeout:()=>1,clearTimeout:()=>{},setBusy:()=>{},setNotice:v=>notice=v,setPending:v=>pending=v,pngData:()=>Promise.resolve('png'),handoff:{clearReview:()=>cleared++,preview:()=>new Promise(done=>resolve=done)}});
 vm.runInContext(code,context);const pendingReview=context.review();await new Promise(done=>setImmediate(done));inputRef.current={file,hands:true,face:false};resolve();await pendingReview;assert.equal(pending,null);assert.equal(cleared,1);assert.match(notice,/입력이 변경/);
});
