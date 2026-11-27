import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import vm from 'node:vm';
import {untilAborted} from '../../gui/managementCommand.js';
import {validVideoJobId} from '../../gui/videoJobId.mjs';
import {restoreLostFocus,visibleFocusTarget} from '../../gui/restoreLostFocus.mjs';

test('영상 편집 검토는 중복 읽기를 막고 시간 초과 후 다시 시도한다',async()=>{
 const source=readFileSync(new URL('../../gui/MiniMaxH3Ref2VAPage.jsx',import.meta.url),'utf8');
 const start=source.indexOf('  async function review(event)'),end=source.indexOf('  useEffect(()=>{if(embedded)return;',start);
 let timer,error='',pending=null,reads=0,slow=true;
 const activeRead={current:null},context=vm.createContext({AbortController,untilAborted,activeRead,reviewOrigin:{current:null},document:{activeElement:{}},busy:false,pending:null,reasons:[],editVersion:{current:0},file:{},prompt:'편집',seed:45,setBusy:()=>{},setError:value=>error=value,setPending:value=>pending=value,setTimeout:fn=>(timer=fn,1),clearTimeout:()=>{},videoData:()=>{reads++;return slow ? new Promise(()=>{}) : Promise.resolve('video');}});
 vm.runInContext(source.slice(start,end),context);
 const event={preventDefault(){}};const first=context.review(event);await context.review(event);assert.equal(reads,1);timer();await first;
 assert.match(error,/시간이 초과/);assert.equal(activeRead.current,null);assert.equal(pending,null);
 slow=false;await context.review(event);assert.equal(pending.edit_video,'video');
});

test('영상 편집 검토 취소는 검토에서 사라진 초점만 복구한다',()=>{
 const source=readFileSync(new URL('../../gui/MiniMaxH3Ref2VAPage.jsx',import.meta.url),'utf8');
 const start=source.indexOf('  function cancelReview()'),end=source.indexOf('  async function readSavedInput(',start);
 for(const moved of [false,true]){
  const body={},inside={},other={},document={body,activeElement:inside};let frame,focused=0;
  const context=vm.createContext({document,restoreLostFocus,visibleFocusTarget,reviewRef:{current:{contains:value=>value===inside}},formRef:{current:{isConnected:true,focus:()=>focused++}},setPending:()=>{},requestAnimationFrame:fn=>frame=fn});
  vm.runInContext(source.slice(start,end),context);context.cancelReview();document.activeElement=moved?other:body;frame();assert.equal(focused,moved?0:1);
 }
});

test('영상 작업 ID는 서버 이력 형식과 정확히 일치해야 한다',()=>{
 const valid='2026-11-24_12-00-00-1234abcd';
 assert.equal(validVideoJobId(valid),true);
 for(const value of ['',null,123,valid+'\n',valid+'x','../'+valid,'2026-11-24_12-00-00-1234ABCD'])assert.equal(validVideoJobId(value),false);
});

test('Wan 영상 화면은 사용자가 수정 후 비운 프롬프트를 늦은 제안으로 채우지 않는다',async()=>{
 for(const name of ['I2VPage.jsx','Wan21VideoPage.jsx'])for(const edited of [false,true]){
  const source=readFileSync(new URL('../../gui/'+name,import.meta.url),'utf8');
  const start=source.indexOf('  useEffect(()=>{\n    let active=true;\n    const controller=new AbortController();\n    (async()=>{try{\n      const scope=generationProposalScope');
  const end=source.indexOf('  async function readSavedInput(',start),code=source.slice(start,end);
  let resolve,cleanup,signal,settings={prompt:''};
  const context=vm.createContext({AbortController,useEffect:fn=>cleanup=fn(),location:{search:''},session:'session',service:'wan22-i2v',promptEdited:{current:false},generationProposalScope:()=>({}),readGenerationProposal:(_command,_scope,options)=>(signal=options.signal,new Promise(done=>resolve=done)),managementCommand:()=>{},wan21ProposalInputs:(_defaults,p)=>p,setSettings:fn=>settings=fn(settings),setError:()=>{}});
  vm.runInContext(code,context);
  if(edited){context.field('prompt','직접 입력');context.field('prompt','');}
  resolve({service:'wan22-i2v',mode:'first_frame',prompt:'제안'});await new Promise(done=>setImmediate(done));
  assert.equal(settings.prompt,edited?'':'제안',name);
  cleanup();assert.equal(signal.aborted,true);
 }
});

test('Wan 제안 조회 중 화면 종료는 신호를 중단하고 늦은 입력을 무시한다',async()=>{
 for(const name of ['I2VPage.jsx','Wan21VideoPage.jsx']){
  const source=readFileSync(new URL('../../gui/'+name,import.meta.url),'utf8');
  const start=source.indexOf('  useEffect(()=>{\n    let active=true;\n    const controller=new AbortController();\n    (async()=>{try{\n      const scope=generationProposalScope');
  const end=source.indexOf('  async function readSavedInput(',start);let cleanup,signal,resolve,updates=0;
  const context=vm.createContext({AbortController,useEffect:fn=>cleanup=fn(),location:{search:''},session:'s',service:'wan22-i2v',promptEdited:{current:false},generationProposalScope:()=>({}),readGenerationProposal:(_command,_scope,options)=>(signal=options.signal,new Promise(done=>resolve=done)),managementCommand:()=>{},wan21ProposalInputs:(_defaults,p)=>p,setSettings:()=>updates++,setError:()=>updates++});
  vm.runInContext(source.slice(start,end),context);cleanup();resolve({service:'wan22-i2v',mode:'first_frame',prompt:'제안'});await new Promise(done=>setImmediate(done));
  assert.equal(signal.aborted,true,name);assert.equal(updates,0,name);
 }
});

test('Wan I2V 저장 입력은 중단을 무시하는 요청과 본문 읽기도 시간 초과한다',async()=>{
 for(const name of ['I2VPage.jsx','Wan21VideoPage.jsx'])for(const stage of ['request','json']){
  const source=readFileSync(new URL('../../gui/'+name,import.meta.url),'utf8');
  const code=source.slice(source.indexOf('  async function readSavedInput('),source.indexOf('  function restoreSavedInput('));
  let timer,resolve;const delayed=new Promise(done=>resolve=done);
  const context=vm.createContext({AbortController,untilAborted,encodeURIComponent,document:{activeElement:{}},currentInput:{current:{busy:false,pending:null}},imageSelectionRevision:{current:0},imageChecking:{current:false},reviewRequest:{current:null},setTimeout:fn=>(timer=fn,1),clearTimeout:()=>{},fetch:()=>stage==='request'?delayed:Promise.resolve({ok:true,json:()=>delayed})});
  vm.runInContext(code,context);const result=context.readSavedInput('job',false);await new Promise(done=>setImmediate(done));timer();
  await assert.rejects(result,/조회 시간이 초과/);resolve({});
 }
});

test('Wan I2V 저장 입력 적용은 조회 중 변경된 입력과 이미지 선택을 보존한다',()=>{
 for(const name of ['I2VPage.jsx','Wan21VideoPage.jsx'])for(const condition of ['unchanged','settings','file','selection','checking','review']){
  const source=readFileSync(new URL('../../gui/'+name,import.meta.url),'utf8');
  const code=source.slice(source.indexOf('  function restoreSavedInput('),source.indexOf('  async function review('));
  const settings={prompt:'현재'},file={},start={settings,file,busy:false,pending:null};
  const current={...start};if(condition==='settings')current.settings={prompt:'변경'};if(condition==='file')current.file={};if(condition==='review')current.pending={};
  let applied=null;const context=vm.createContext({currentInput:{current},imageChecking:{current:condition==='checking'},reviewRequest:{current:null},imageSelectionRevision:{current:condition==='selection'?1:0},promptEdited:{current:false},nonLightningSettings:{current:null},usesAttack:true,setAttackModel:()=>{},setAttackError:()=>{},setSettings:value=>applied=value,setFile:()=>{},setError:()=>{},setNotice:()=>{},inputCardRef:{current:null},requestAnimationFrame:()=>{}});
  vm.runInContext(code,context);
  const record={id:'job',inputAtStart:start,selectionAtStart:0,restoredFile:{}},request={prompt:'저장',action:'generate',images:[],width:832,height:480};
  if(condition==='unchanged'){context.restoreSavedInput(request,record);assert.equal(applied.prompt,'저장');assert.equal(context.promptEdited.current,true);}
  else{assert.throws(()=>context.restoreSavedInput(request,record),/변경되어 적용하지/);assert.equal(applied,null);}
 }
});

test('Wan 영상 검토는 중복 확인을 막고 시간 초과 또는 입력 변경 시 기존 입력을 유지한다',async()=>{
 for(const name of ['I2VPage.jsx','Wan21VideoPage.jsx'])for(const outcome of ['timeout','changed','success']){
  const source=readFileSync(new URL('../../gui/'+name,import.meta.url),'utf8');
  const code=source.slice(source.indexOf('  async function review(event)'),source.indexOf('  async function submit()'));
  const settings={prompt:'동작'},file={};let finish,timer,calls=0,busy=false,error='',pending=null;
  const currentInput={current:{settings,file}};
  const context=vm.createContext({AbortController,untilAborted,document:{activeElement:{}},settings,file,currentInput,isImage:true,busy:false,pending:null,reasons:[],inputReasons:[],imageChecking:{current:false},imageSelectionRevision:{current:0},reviewRequest:{current:null},reviewOrigin:{current:null},setTimeout:fn=>(timer=fn,1),clearTimeout:()=>{},setError:value=>error=value,setBusy:value=>busy=value,setPending:value=>pending=value,referencePng:()=>{calls++;return new Promise(done=>finish=done);}});
  vm.runInContext(code,context);const result=context.review({preventDefault(){}});await context.review({preventDefault(){}});assert.equal(calls,1);
  if(outcome==='timeout')timer();else {if(outcome==='changed')currentInput.current={settings:{prompt:'변경'},file};finish('image');}
  await result;assert.equal(busy,false);assert.equal(context.reviewRequest.current,null);
  if(outcome==='success')assert.equal(pending.prompt,'동작');else{assert.equal(pending,null);assert.match(error,outcome==='timeout'?/시간이 초과/:/바뀌었습니다/);}
 }
});

test('Wan 2.1 텍스트 검토는 이미지 변환 없이 입력을 보존해 검토한다',async()=>{
 const source=readFileSync(new URL('../../gui/Wan21VideoPage.jsx',import.meta.url),'utf8');
 const code=source.slice(source.indexOf('  async function review(event)'),source.indexOf('  async function submit()'));
 const settings={prompt:'동작'},file=null;let pending=null,calls=0;
 const context=vm.createContext({AbortController,untilAborted,document:{activeElement:{}},settings,file,currentInput:{current:{settings,file}},isImage:false,busy:false,pending:null,inputReasons:[],imageChecking:{current:false},imageSelectionRevision:{current:0},reviewRequest:{current:null},reviewOrigin:{current:null},setTimeout:()=>1,clearTimeout:()=>{},setError:()=>{},setBusy:()=>{},setPending:value=>pending=value,referencePng:()=>calls++});
 vm.runInContext(code,context);await context.review({preventDefault(){}});assert.equal(calls,0);assert.equal(pending.prompt,'동작');assert.equal(pending.images.length,0);
});

test('Wan 영상 검토 중 화면 종료는 늦은 이미지 결과를 적용하지 않는다',async()=>{
 for(const name of ['I2VPage.jsx','Wan21VideoPage.jsx']){
  const source=readFileSync(new URL('../../gui/'+name,import.meta.url),'utf8');
  const code=source.slice(source.indexOf('  async function review(event)'),source.indexOf('  async function submit()'));
  const cleanup=source.match(/useEffect\(\(\)=>\(\)=>\{reviewRequest\.current\?\.abort\(\);reviewRequest\.current=null;\},\[\]\);/)[0];
  const settings={prompt:'동작'},file={};let finish,close,pending=null,error='';
  const context=vm.createContext({AbortController,untilAborted,document:{activeElement:{}},settings,file,currentInput:{current:{settings,file}},isImage:true,busy:false,pending:null,reasons:[],inputReasons:[],imageChecking:{current:false},imageSelectionRevision:{current:0},reviewRequest:{current:null},reviewOrigin:{current:null},useEffect:fn=>close=fn(),setTimeout:()=>1,clearTimeout:()=>{},setError:value=>error=value,setBusy:()=>{},setPending:value=>pending=value,referencePng:()=>new Promise(done=>finish=done)});
  vm.runInContext(code,context);vm.runInContext(cleanup,context);const waiting=context.review({preventDefault(){}});close();finish('image');await waiting;
  assert.equal(pending,null);assert.equal(error,'');
 }
});

test('Wan 영상 접수는 중복을 막고 처리 표시를 유지하며 불확실한 응답에 이력 확인을 안내한다',async()=>{
 for(const name of ['I2VPage.jsx','Wan21VideoPage.jsx'])for(const outcome of ['timeout','invalid','success']){
  const source=readFileSync(new URL('../../gui/'+name,import.meta.url),'utf8');
  const code=source.slice(source.indexOf('  async function submit()'),source.indexOf('  return <article'));
  let resolve,timer,calls=0,pending={action:'generate'},busy=false,error='',notice='',job='';
  const context=vm.createContext({AbortController,untilAborted,validVideoJobId,document:{body:{},activeElement:{}},service:'wan',pending,model:{},generationReady:()=>true,attackReason:'',isImage:true,sending:{current:false},reviewRef:{current:{contains:()=>false}},formRef:{current:null},requestAnimationFrame:()=>{},setTimeout:fn=>(timer=fn,1),clearTimeout:()=>{},managementCommand:()=>{calls++;return new Promise(done=>resolve=done);},setBusy:value=>busy=value,setPending:value=>pending=value,setError:value=>error=value,setNotice:value=>notice=value,setJob:value=>job=value,setRevision:()=>{}});
  vm.runInContext(code,context);const result=context.submit();await context.submit();assert.equal(calls,1);assert.equal(busy,true);assert.notEqual(pending,null);
  if(outcome==='timeout')timer();else resolve(outcome==='success'?{id:'2026-11-24_12-00-00-1234abcd'}:{id:'잘못된-ID'});
  await result;assert.equal(busy,false);assert.equal(pending,null);assert.equal(context.sending.current,false);
  if(outcome==='success'){assert.equal(job,'2026-11-24_12-00-00-1234abcd');assert.match(notice,/접수했습니다/);}else assert.match(error,/접수 여부가 불확실.*이력/);
 }
});

test('Wan 검토 취소는 사라진 초점만 입력으로 돌리고 사용자가 이동한 초점은 유지한다',()=>{
 for(const name of ['I2VPage.jsx','Wan21VideoPage.jsx'])for(const moved of [false,true]){
  const source=readFileSync(new URL('../../gui/'+name,import.meta.url),'utf8');
  const code=source.slice(source.indexOf('  function cancelReview()'),source.indexOf('  async function submit()'));
  const body={},close={},other={};let frame,focused=0,pending={};const document={body,activeElement:close};
  const target={disabled:false,focus:()=>focused++};
  const context=vm.createContext({document,reviewRef:{current:{contains:node=>node===close}},inputCardRef:{current:{open:false}},formRef:{current:{querySelector:()=>target}},setPending:value=>pending=value,requestAnimationFrame:fn=>frame=fn});
  vm.runInContext(code,context);context.cancelReview();document.activeElement=moved?other:body;frame();
  assert.equal(pending,null);assert.equal(context.inputCardRef.current.open,true);assert.equal(focused,moved?0:1);
 }
});
