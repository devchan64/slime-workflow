import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import vm from 'node:vm';
import {untilAborted} from '../../gui/managementCommand.js';

test('검색 결과에서 사라진 FLUX 가이드는 적용하지 않는다',async()=>{
 const source=readFileSync(new URL('../../gui/FluxImagePage.jsx',import.meta.url),'utf8');
 const method=source.slice(source.indexOf('  async function applyReferenceGuide()'),source.indexOf('  async function runInputTool('));
 let calls=0,notice='',error=false;
 const context=vm.createContext({guideRequest:{current:null},interactionRef:{current:{busy:false,review:null}},guideAvailable:false,setGuideError:value=>error=value,setGuideNotice:value=>notice=value,fetch:()=>calls++});
 vm.runInContext(method,context);await context.applyReferenceGuide();assert.equal(calls,0);assert.equal(error,true);assert.match(notice,/다시 선택/);
});

test('이미지 확인 중 가이드 적용 안내는 이전 오류 상태를 해제한다',async()=>{
 const source=readFileSync(new URL('../../gui/FluxImagePage.jsx',import.meta.url),'utf8');
 const method=source.slice(source.indexOf('  async function applyReferenceGuide()'),source.indexOf('  async function runInputTool('));
 let error=true,notice='';const context=vm.createContext({guideRequest:{current:null},interactionRef:{current:{busy:false,review:null}},guideAvailable:true,checkingSlots:{current:new Set([0])},setGuideError:value=>error=value,setGuideNotice:value=>notice=value});
 vm.runInContext(method,context);await context.applyReferenceGuide();assert.equal(error,false);assert.match(notice,/이미지 확인/);
});

test('FLUX 참조 도구는 각 서비스 응답을 해당 입력에 적용한다',async()=>{
 const source=readFileSync(new URL('../../gui/FluxImagePage.jsx',import.meta.url),'utf8');
 const code=source.slice(source.indexOf('  async function runInputTool('),source.indexOf('  async function preview('));
 for(const kind of ['face','stage','billboard']){
  let files=[],form={prompt:'original'},notice='';
  const context=vm.createContext({AbortController,untilAborted,document:{activeElement:null},toolFocus:{current:null},inputFormRef:{current:null},guideRequest:{current:null},imageSelectionRevision:{current:0},interactionRef:{current:{busy:false,review:null}},checkingSlots:{current:new Set()},stage:'face',layout:'3x1',subject:'house',setToolNotice:value=>notice=value,setToolError:()=>{},setToolLoading:()=>{},setBusy:()=>{},setFiles:value=>files=typeof value==='function'?value(files):value,setForm:value=>form=typeof value==='function'?value(form):value,edit:(key,value)=>form={...form,[key]:value},setTimeout:()=>1,clearTimeout:()=>{},File:class{constructor(parts,name){this.name=name;}},pngFile:(_data,name)=>({name}),fetch:async url=>({ok:true,blob:async()=>({}),json:async()=>url.includes('mannequin')?{prompt:'stage prompt',width:768,height:1152,images:['encoded']}:{prompt:'guide prompt',image:'encoded'}})});
  vm.runInContext(code,context);await context[kind==='face'?'defaultFace':kind==='stage'?'applyStage':'applyGuide']();
  assert.match(notice,/적용했습니다/);assert.equal(files.length,1);
  if(kind==='stage'){assert.equal(form.prompt,'stage prompt');assert.equal(form.width,768);}if(kind==='billboard')assert.equal(form.prompt,'guide prompt');
 }
});

test('FLUX 공통 참조 도구는 시간 초과와 화면 종료 후 늦은 결과를 적용하지 않는다',async()=>{
 const source=readFileSync(new URL('../../gui/FluxImagePage.jsx',import.meta.url),'utf8');
 const method=source.slice(source.indexOf('  async function runInputTool('),source.indexOf('  function defaultFace()'));
 for(const mode of ['timeout','unmount','changed']){
  let timer,finish,applied=0,notice='';const guideRequest={current:null},imageSelectionRevision={current:0};
  const context=vm.createContext({AbortController,untilAborted,document:{activeElement:null},toolFocus:{current:null},inputFormRef:{current:null},guideRequest,imageSelectionRevision,interactionRef:{current:{busy:false,review:null}},checkingSlots:{current:new Set()},setToolNotice:value=>notice=value,setToolError:()=>{},setToolLoading:()=>{},setBusy:()=>{},setTimeout:fn=>(timer=fn,1),clearTimeout:()=>{}});
  vm.runInContext(method,context);const pending=context.runInputTool(()=>new Promise(resolve=>finish=resolve));
  if(mode==='timeout')timer();else if(mode==='unmount'){const request=guideRequest.current;guideRequest.current=null;request.abort();}else imageSelectionRevision.current++;
  finish(()=>applied++);await pending;assert.equal(applied,0);
  if(mode==='timeout')assert.match(notice,/시간이 초과/);if(mode==='changed')assert.match(notice,/변경/);
 }
});

test('FLUX 참조 가이드 요청은 중복을 막고 시간 초과 시 입력을 유지한다',async()=>{
 const source=readFileSync(new URL('../../gui/FluxImagePage.jsx',import.meta.url),'utf8');
 const method=source.slice(source.indexOf('  async function applyReferenceGuide()'),source.indexOf('  async function runInputTool('));
 for(const phase of ['fetch','body']){
  let timer,busy=false,notice='',error=false,applied=0,calls=0;const guideRequest={current:null};
  const context=vm.createContext({AbortController,untilAborted,document:{activeElement:null},toolFocus:{current:null},inputFormRef:{current:null},guideRequest,interactionRef:{current:{busy:false,review:null}},checkingSlots:{current:new Set()},imageSelectionRevision:{current:0},selectedGuide:'guide',guideAvailable:true,guideUrl:id=>id,profile:{},setBusy:value=>busy=value,setNotice:()=>{},setGuideNotice:value=>notice=value,setGuideError:value=>error=value,setFiles:()=>applied++,setForm:()=>{},setTimeout:fn=>(timer=fn,1),clearTimeout:()=>{},fetch:()=>{calls++;return phase==='fetch'?new Promise(()=>{}):Promise.resolve({ok:true,blob:()=>new Promise(()=>{})});}});
  vm.runInContext(method,context);const request=context.applyReferenceGuide();await context.applyReferenceGuide();assert.equal(calls,1);assert.equal(busy,true);
  timer();await request;assert.equal(busy,false);assert.equal(error,true);assert.match(notice,/시간이 초과/);assert.equal(applied,0);assert.equal(guideRequest.current,null);
 }
});

test('FLUX 가이드의 늦은 응답은 이미지 선택 변경 또는 화면 종료 후 적용하지 않는다',async()=>{
 const source=readFileSync(new URL('../../gui/FluxImagePage.jsx',import.meta.url),'utf8');
 const method=source.slice(source.indexOf('  async function applyReferenceGuide()'),source.indexOf('  async function runInputTool('));
 for(const mode of ['changed','unmount']){
  let finish,applied=0,notice='',errors=0;const guideRequest={current:null},imageSelectionRevision={current:0};
  const context=vm.createContext({AbortController,untilAborted,document:{activeElement:null},toolFocus:{current:null},inputFormRef:{current:null},guideRequest,imageSelectionRevision,interactionRef:{current:{busy:false,review:null}},checkingSlots:{current:new Set()},selectedGuide:'guide',guideAvailable:true,guideUrl:id=>id,profile:{},setBusy:()=>{},setNotice:()=>{},setGuideNotice:value=>notice=value,setGuideError:value=>{if(value)errors++;},setFiles:()=>applied++,setForm:()=>{},setTimeout:()=>1,clearTimeout:()=>{},fetch:()=>new Promise(resolve=>finish=resolve)});
  vm.runInContext(method,context);const pending=context.applyReferenceGuide();
  if(mode==='changed')imageSelectionRevision.current++;else{const request=guideRequest.current;guideRequest.current=null;request.abort();}
  finish({ok:true,blob:async()=>({})});await pending;
  assert.equal(applied,0);if(mode==='changed'){assert.match(notice,/변경/);assert.equal(errors,1);}else assert.equal(errors,0);
 }
});

test('참조 입력 도구 연결 실패는 공통 안내를 표시한다',async()=>{
 const source=readFileSync(new URL('../../gui/FluxImagePage.jsx',import.meta.url),'utf8');
 const method=source.slice(source.indexOf('  async function runInputTool('),source.indexOf('  function defaultFace()',source.indexOf('  async function runInputTool(')));
 let notice='',isError=false;
 const context=vm.createContext({AbortController,TypeError,untilAborted,document:{activeElement:null},toolFocus:{current:null},inputFormRef:{current:null},guideRequest:{current:null},imageSelectionRevision:{current:0},interactionRef:{current:{busy:false,review:null}},checkingSlots:{current:new Set()},setTimeout:()=>1,clearTimeout:()=>{},setBusy:()=>{},setToolLoading:()=>{},setToolError:value=>isError=value,setToolNotice:value=>notice=value,requestErrorMessage:()=> '서버에 연결할 수 없습니다. 연결 상태를 확인하세요.'});
 vm.runInContext(method,context);await context.runInputTool(async()=>{throw new TypeError('Failed to fetch');});
 assert.equal(isError,true);assert.match(notice,/연결 상태/);assert.doesNotMatch(notice,/Failed to fetch/);
});

test('가이드 적용 연결 실패는 선택을 유지하고 공통 안내를 표시한다',async()=>{
 const source=readFileSync(new URL('../../gui/FluxImagePage.jsx',import.meta.url),'utf8');
 const method=source.slice(source.indexOf('  async function applyReferenceGuide()'),source.indexOf('  async function runInputTool('));
 let notice='',isError=false,applied=false;
 const context=vm.createContext({AbortController,TypeError,untilAborted,document:{activeElement:null},toolFocus:{current:null},inputFormRef:{current:null},guideRequest:{current:null},imageSelectionRevision:{current:0},interactionRef:{current:{busy:false,review:null}},checkingSlots:{current:new Set()},selectedGuide:'guide',guideAvailable:true,guideUrl:id=>id,profile:{},setTimeout:()=>1,clearTimeout:()=>{},setBusy:()=>{},setNotice:()=>{},setGuideError:value=>isError=value,setGuideNotice:value=>notice=value,setFiles:()=>{applied=true;},requestErrorMessage:()=> '서버에 연결할 수 없습니다. 연결 상태를 확인하세요.',fetch:async()=>{throw new TypeError('Failed to fetch');}});
 vm.runInContext(method,context);await context.applyReferenceGuide();
 assert.equal(isError,true);assert.match(notice,/연결 상태/);assert.doesNotMatch(notice,/Failed to fetch/);assert.equal(applied,false);assert.equal(context.selectedGuide,'guide');
});
