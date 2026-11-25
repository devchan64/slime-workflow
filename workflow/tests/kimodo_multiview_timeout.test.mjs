import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import vm from 'node:vm';
import {untilAborted} from '../../gui/managementCommand.js';

test('다중 시점 검수는 파일 읽기와 서버 응답 지연 시 대기를 해제하고 보고서를 유지한다',async()=>{
 const source=readFileSync(new URL('../../gui/KimodoMultiviewReport.jsx',import.meta.url),'utf8');
 const code=source.slice(source.indexOf('  async function load(event)'),source.indexOf('  return <details className="kimodo-multiview">'));
 for(const stage of ['file','request','json']){
  let timer,resolve,error='',busy=false,report='previous';
  const delayed=()=>new Promise(done=>resolve=done);
  const file={text:()=>stage==='file'?delayed():Promise.resolve('{}')};
  const response={ok:true,json:()=>stage==='json'?delayed():Promise.resolve({views:[{angle:0,rows:[]}],limitations:[]})};
  const context=vm.createContext({AbortController,untilAborted,pending:{current:null},dirtyRef:{current:false},restoreFocus:{current:false},submitRef:{current:{}},document:{activeElement:null},setTimeout:fn=>(timer=fn,1),clearTimeout:()=>{},files:{observations:file,skeleton:{text:async()=> '{}'}},
   fetch:()=>stage==='request'?delayed():Promise.resolve(response),setBusy:value=>busy=value,setError:value=>error=value,setView:()=>{},setReport:value=>report=value});
  vm.runInContext(code,context);const waiting=context.load({preventDefault(){}});await new Promise(done=>setImmediate(done));timer();await waiting;
  assert.equal(busy,false);assert.match(error,/시간이 초과/);assert.equal(report,'previous');resolve(response);await new Promise(done=>setImmediate(done));assert.equal(report,'previous');
 }
});

test('다중 시점 검수는 잘못된 보고서를 거부하고 정상 보고서만 편집 상태를 새로 연다',async()=>{
 const source=readFileSync(new URL('../../gui/KimodoMultiviewReport.jsx',import.meta.url),'utf8');
 const code=source.slice(source.indexOf('  async function load(event)'),source.indexOf('  return <details className="kimodo-multiview">'));
 for(const valid of [false,true]){
  let error='',report='previous',revision=0;
  const result=valid?{views:[{angle:0,rows:[['0','1']]}],limitations:[]}:{views:[{angle:0,rows:[[{}]]}],limitations:[]};
  const context=vm.createContext({AbortController,untilAborted,pending:{current:null},dirtyRef:{current:false},restoreFocus:{current:false},submitRef:{current:{}},document:{activeElement:null},setTimeout:()=>1,clearTimeout:()=>{},files:{observations:{text:async()=> '{}'},skeleton:{text:async()=> '{}'}},fetch:async()=>({ok:true,json:async()=>result}),
   setBusy:()=>{},setError:value=>error=value,setView:()=>{},setReport:value=>report=value,setReportRevision:fn=>revision=fn(revision)});
  vm.runInContext(code,context);await context.load({preventDefault(){}});
  if(valid){assert.equal(report,result);assert.equal(revision,1);assert.equal(error,'');}
  else{assert.equal(report,'previous');assert.equal(revision,0);assert.match(error,/형식/);}
 }
});

test('가중치 편집 중에는 보고서 재조회가 시작되지 않는다',async()=>{
 const source=readFileSync(new URL('../../gui/KimodoMultiviewReport.jsx',import.meta.url),'utf8');
 const code=source.slice(source.indexOf('  async function load(event)'),source.indexOf('  return <details className="kimodo-multiview">'));
 let calls=0;const context=vm.createContext({pending:{current:null},dirtyRef:{current:true},setBusy:()=>calls++});
 vm.runInContext(code,context);await context.load({preventDefault(){}});assert.equal(calls,0);
});

test('표시 방향과 다르거나 관절 번호가 잘못된 가중치는 보고서를 교체하지 않는다',async()=>{
 const source=readFileSync(new URL('../../gui/KimodoMultiviewReport.jsx',import.meta.url),'utf8');
 const code=source.slice(source.indexOf('  async function load(event)'),source.indexOf('  return <details className="kimodo-multiview">'));
 for(const defect of ['extra','observation','joint','count']){
  let error='',report='previous';
  const row={observation:1,joints:Array.from({length:18},(_,joint)=>({joint,weight:1,reason:'ok'}))};
  const result={views:[{angle:0,rows:[]}],limitations:[],joint_weights:{views:[row]}};
  if(defect==='extra')result.joint_weights.views.push(structuredClone(row));
  if(defect==='observation')row.observation=2;
  if(defect==='joint')row.joints[3].joint=2;
  if(defect==='count')row.joints.pop();
  const context=vm.createContext({AbortController,untilAborted,pending:{current:null},dirtyRef:{current:false},restoreFocus:{current:false},submitRef:{current:{}},document:{activeElement:null},setTimeout:()=>1,clearTimeout:()=>{},files:{observations:{text:async()=> '{}'},skeleton:{text:async()=> '{}'}},fetch:async()=>({ok:true,json:async()=>result}),
   setBusy:()=>{},setError:value=>error=value,setView:()=>{},setReport:value=>report=value,setReportRevision:()=>{}});
  vm.runInContext(code,context);await context.load({preventDefault(){}});
  assert.equal(report,'previous');assert.match(error,/형식/);
 }
});

test('필수 검수 파일이 없으면 서버 요청 없이 필요한 파일을 안내한다',async()=>{
 const source=readFileSync(new URL('../../gui/KimodoMultiviewReport.jsx',import.meta.url),'utf8');
 const code=source.slice(source.indexOf('  async function load(event)'),source.indexOf('  return <details className="kimodo-multiview">'));
 let error='';const context=vm.createContext({pending:{current:null},dirtyRef:{current:false},files:{observations:{}},setError:value=>error=value});
 vm.runInContext(code,context);await context.load({preventDefault(){}});assert.match(error,/참조 관절 JSON.*3D 골격 JSON/);
});

test('보고서 조회 도중 편집이 시작되면 늦은 응답은 편집을 덮어쓰지 않는다',async()=>{
 const source=readFileSync(new URL('../../gui/KimodoMultiviewReport.jsx',import.meta.url),'utf8');
 const code=source.slice(source.indexOf('  async function load(event)'),source.indexOf('  return <details className="kimodo-multiview">'));
 let resolve,error='',report='previous',revision=0;
 const context=vm.createContext({AbortController,untilAborted,pending:{current:null},dirtyRef:{current:false},restoreFocus:{current:false},submitRef:{current:{}},document:{activeElement:null},setTimeout:()=>1,clearTimeout:()=>{},files:{observations:{text:async()=> '{}'},skeleton:{text:async()=> '{}'}},
  fetch:()=>new Promise(done=>resolve=done),setBusy:()=>{},setError:value=>error=value,setView:()=>{},setReport:value=>report=value,setReportRevision:fn=>revision=fn(revision)});
 vm.runInContext(code,context);const waiting=context.load({preventDefault(){}});await new Promise(done=>setImmediate(done));context.dirtyRef.current=true;
 resolve({ok:true,json:async()=>({views:[{angle:0,rows:[]}],limitations:[]})});await waiting;
 assert.equal(report,'previous');assert.equal(revision,0);assert.match(error,/편집 내용을 유지/);
});

test('가중치 편집이나 조회 중 파일 변경은 기존 입력과 보고서를 유지한다',()=>{
 const source=readFileSync(new URL('../../gui/KimodoMultiviewReport.jsx',import.meta.url),'utf8');
 const code=source.slice(source.indexOf('  function changeFile('),source.indexOf('  async function load('));
 for(const [dirty,pending] of [[true,false],[false,true],[false,false]]){
  let files={observations:'old'},report='previous';
  const context=vm.createContext({dirtyRef:{current:dirty},pending:{current:pending?{}:null},setFiles:fn=>files=fn(files),setReport:value=>report=value,setError:()=>{}});
  vm.runInContext(code,context);context.changeFile('observations','new');
  assert.equal(files.observations,dirty||pending?'old':'new');assert.equal(report,dirty||pending?'previous':null);
 }
});

test('파일 선택을 취소하면 기존 파일과 보고서를 유지한다',()=>{
 const source=readFileSync(new URL('../../gui/KimodoMultiviewReport.jsx',import.meta.url),'utf8');
 const code=source.slice(source.indexOf('  function changeFile('),source.indexOf('  async function load('));
 let changes=0;const context=vm.createContext({dirtyRef:{current:false},pending:{current:null},setFiles:()=>changes++,setReport:()=>changes++,setError:()=>changes++});
 vm.runInContext(code,context);context.changeFile('image',undefined);assert.equal(changes,0);
});

test('선택 파일 제거는 잠금 상태를 지키고 입력과 보고서를 함께 비운다',()=>{
 const source=readFileSync(new URL('../../gui/KimodoMultiviewReport.jsx',import.meta.url),'utf8');
 const code=source.slice(source.indexOf('  function removeFile('),source.indexOf('  async function load('));
 for(const locked of [true,false]){
  const button={},body={},input={value:'selected',focus(){focused=true;}};let files={heldout:{name:'file'}},report='old',focused=false,frame;
  const document={activeElement:button,body};
  const context=vm.createContext({dirtyRef:{current:locked},pending:{current:null},fileRefs:{current:{heldout:input}},document,requestAnimationFrame:fn=>frame=fn,
   setFiles:fn=>files=fn(files),setReport:value=>report=value,setError:()=>{}});
  vm.runInContext(code,context);context.removeFile('heldout',button);
  if(locked){assert.ok(files.heldout);assert.equal(report,'old');assert.equal(input.value,'selected');}
  else{assert.equal(files.heldout,undefined);assert.equal(report,null);assert.equal(input.value,'');document.activeElement=body;frame();assert.equal(focused,true);}
 }
});

test('가중치 검증의 요청과 응답 지연은 편집 내용을 유지하고 대기를 해제한다',async()=>{
 const source=readFileSync(new URL('../../gui/KimodoJointWeights.jsx',import.meta.url),'utf8');
 const code=source.slice(source.indexOf('  async function validate()'),source.indexOf('  return <details className="kimodo-joint-weights">'));
 for(const stage of ['request','json']){
  let timer,resolve,error='',busy=false,download='old';
  const delayed=()=>new Promise(done=>resolve=done),response={ok:true,json:()=>stage==='json'?delayed():Promise.resolve({views:[]})};
  const context=vm.createContext({AbortController,untilAborted,pending:{current:null},disabled:false,validateRef:{current:{}},restoreFocus:{current:false},document:{activeElement:null},weights:{views:[]},setTimeout:fn=>(timer=fn,1),clearTimeout:()=>{},
   fetch:()=>stage==='request'?delayed():Promise.resolve(response),setBusy:value=>busy=value,setError:value=>error=value,setInvalidTarget:()=>{},setDownload:value=>download=value});
  vm.runInContext(code,context);const waiting=context.validate();await new Promise(done=>setImmediate(done));timer();await waiting;
  assert.equal(busy,false);assert.match(error,/시간이 초과/);assert.equal(download,'');resolve(response);await new Promise(done=>setImmediate(done));assert.equal(download,'');
 }
});

test('가중치 검증 결과가 입력과 일치할 때만 다운로드를 제공한다',async()=>{
 const source=readFileSync(new URL('../../gui/KimodoJointWeights.jsx',import.meta.url),'utf8');
 const code=source.slice(source.indexOf('  async function validate()'),source.indexOf('  return <details className="kimodo-joint-weights">'));
 const weights={schema:'schema',views:[{observation:1,joints:[{joint:0,weight:0.5,reason:'ok'}]}]};
 for(const valid of [true,false]){
  let error='',download='';const checked=structuredClone(weights);if(!valid)checked.views[0].joints[0].weight=0.8;
  const context=vm.createContext({AbortController,untilAborted,pending:{current:null},disabled:false,validateRef:{current:{}},restoreFocus:{current:false},document:{activeElement:null},weights,setTimeout:()=>1,clearTimeout:()=>{},
   fetch:async()=>({ok:true,json:async()=>checked}),setBusy:()=>{},setError:value=>error=value,setInvalidTarget:()=>{},setDownload:value=>download=value,
   URL:{createObjectURL:()=> 'blob:validated'},Blob});
  vm.runInContext(code,context);await context.validate();
  if(valid){assert.equal(download,'blob:validated');assert.equal(error,'');}else{assert.equal(download,'');assert.match(error,/일치하지/);}
 }
});

test('다른 방향의 잘못된 가중치와 빈 근거는 위치를 안내하고 요청하지 않는다',async()=>{
 const source=readFileSync(new URL('../../gui/KimodoJointWeights.jsx',import.meta.url),'utf8');
 const code=source.slice(source.indexOf('  async function validate()'),source.indexOf('  return <details className="kimodo-joint-weights">'));
 for(const [weight,reason,expected] of [['','ok',/가중치/],[1.1,'ok',/가중치/],[0.5,'  ',/판단 근거/]]){
  let error='',download='old',calls=0,target=null;
  const weights={views:[{joints:[{joint:0,weight:0.5,reason:'ok'}]},{joints:[{joint:3,weight,reason}]}]};
  const context=vm.createContext({pending:{current:null},disabled:false,weights,setError:value=>error=value,setInvalidTarget:value=>target=value,setDownload:value=>download=value,fetch:()=>calls++});
  vm.runInContext(code,context);await context.validate();
  assert.match(error,/관측 2 · 3번 관절/);assert.match(error,expected);assert.equal(calls,0);assert.equal(download,'');
  assert.deepEqual({...target},{view:1,joint:3,field:reason.trim()?'weight':'reason'});
 }
});

test('오류 입력 이동은 해당 관측이 표시된 뒤 해당 필드에 초점을 준다',()=>{
 const source=readFileSync(new URL('../../gui/KimodoJointWeights.jsx',import.meta.url),'utf8');
 const effect=source.match(/useEffect\(\(\)=>\{if\(focusTarget && focusTarget\.view===view\).*?\},\[focusTarget,view\]\);/)[0];
 let focused=0,cleared=false;
 const context=vm.createContext({useEffect:fn=>fn(),focusTarget:{view:1,joint:3,field:'reason'},view:0,inputRefs:{current:{'3:reason':{focus:()=>focused++}}},setFocusTarget:()=>cleared=true});
 vm.runInContext(effect,context);assert.equal(focused,0);assert.equal(cleared,false);
 context.view=1;vm.runInContext(effect,context);assert.equal(focused,1);assert.equal(cleared,true);
});

test('가중치 검증 후 사라진 초점만 검증 버튼으로 복구한다',()=>{
 const source=readFileSync(new URL('../../gui/KimodoJointWeights.jsx',import.meta.url),'utf8');
 const effect=source.match(/useEffect\(\(\)=>\{if\(!busy && restoreFocus\.current\).*?\},\[busy\]\);/)[0];
 for(const moved of [true,false]){
  const body={},other={};let focused=false;
  const context=vm.createContext({useEffect:fn=>fn(),busy:false,restoreFocus:{current:true},document:{body,activeElement:moved?other:body},validateRef:{current:{focus:()=>focused=true}}});
  vm.runInContext(effect,context);assert.equal(focused,!moved);assert.equal(context.restoreFocus.current,false);
 }
});

test('보고서 조회 종료 시 편집 상태에 맞는 곳으로 사라진 초점만 복구한다',()=>{
 const source=readFileSync(new URL('../../gui/KimodoMultiviewReport.jsx',import.meta.url),'utf8');
 const effect=source.match(/useEffect\(\(\)=>\{if\(!busy && restoreFocus\.current\).*?\},\[busy,weightsDirty\]\);/)[0];
 for(const dirty of [true,false])for(const moved of [true,false]){
  const body={},other={};let focused='';
  const context=vm.createContext({useEffect:fn=>fn(),busy:false,weightsDirty:dirty,restoreFocus:{current:true},document:{body,activeElement:moved?other:body},
   dirtyNoticeRef:{current:{focus:()=>focused='notice'}},submitRef:{current:{focus:()=>focused='submit'}}});
  vm.runInContext(effect,context);assert.equal(focused,moved?'':dirty?'notice':'submit');
 }
});

test('가중치 검증 중 빠른 편집과 취소는 차단하고 이후 취소는 원본을 복구한다',()=>{
 const source=readFileSync(new URL('../../gui/KimodoJointWeights.jsx',import.meta.url),'utf8');
 const code=source.slice(source.indexOf('  function edit('),source.indexOf('  async function validate()'));
 const initial={views:[{joints:[{joint:0,weight:0.5,reason:'original'}]}]};
 let current=initial,dirty=false;
 const context=vm.createContext({pending:{current:{}},disabled:false,initial,weights:initial,view:0,invalidTarget:null,setWeights:value=>current=value,setDownload:()=>{},setInvalidTarget:()=>{},setError:()=>{},onDirtyChange:value=>dirty=value});
 vm.runInContext(code,context);context.edit(0,'weight',0.7);context.reset();assert.equal(current,initial);assert.equal(dirty,false);
 context.pending.current=null;context.edit(0,'weight',0.7);assert.equal(current.views[0].joints[0].weight,0.7);assert.equal(dirty,true);
 context.reset();assert.equal(current,initial);assert.equal(dirty,false);
});

test('다른 입력을 고쳐도 가중치 오류 안내는 유지하고 해당 입력을 고칠 때만 해제한다',()=>{
 const source=readFileSync(new URL('../../gui/KimodoJointWeights.jsx',import.meta.url),'utf8');
 const code=source.slice(source.indexOf('  function edit('),source.indexOf('  async function validate()'));
 let error='오류',target={view:0,joint:0,field:'reason'};
 const weights={views:[{joints:[{joint:0,weight:0.5,reason:''},{joint:1,weight:0.5,reason:'ok'}]}]};
 const context=vm.createContext({pending:{current:null},disabled:false,weights,view:0,invalidTarget:target,setWeights:()=>{},setDownload:()=>{},setInvalidTarget:value=>target=value,setError:value=>error=value,onDirtyChange:()=>{}});
 vm.runInContext(code,context);context.edit(1,'reason','수정');assert.equal(error,'오류');assert.notEqual(target,null);
 context.edit(0,'reason','수정');assert.equal(error,'');assert.equal(target,null);
});
