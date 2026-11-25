import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import vm from 'node:vm';
import {untilAborted} from '../../gui/managementCommand.js';
import {validVideoJobId} from '../../gui/videoJobId.mjs';
import {restoreLostFocus,visibleFocusTarget} from '../../gui/restoreLostFocus.mjs';

const source=readFileSync(new URL('../../gui/MiniMaxH3Page.jsx',import.meta.url),'utf8');
const code=source.slice(source.indexOf('  async function readSavedInput('),source.indexOf('  function restoreSavedInput('));
const request={action:'generate',prompt:'move',images:['YQ=='],width:832,height:480,frames:124,steps:8,seed:42};
function contextFor(response,timer){
 return vm.createContext({AbortController,untilAborted,Uint8Array,atob,File,encodeURIComponent,document:{activeElement:{}},current:{current:{busy:false,pending:null,checking:false}},reviewRequest:{current:null},imageVersion:{current:0},fetch:()=>response,setTimeout:timer,clearTimeout:()=>{}});
}
test('MiniMax 저장 입력은 지원 설정만 적용 대상으로 읽고 구형 크기는 상세 확인만 허용한다',async()=>{
 for(const field of ['width','height','frames','steps','seed','prompt','action']){
  const bad={...request,[field]:field==='prompt'?'':field==='action'?'other':-1};
  const context=contextFor(Promise.resolve({ok:true,json:async()=>({id:'job',request:bad})}),()=>1);
  vm.runInContext(code,context);await assert.rejects(context.readSavedInput('job'),/지원하지 않는 저장 설정/);
 }
 const legacy={...request,width:768,height:448};
 const context=contextFor(Promise.resolve({ok:true,json:async()=>({id:'job',request:legacy})}),()=>1);
 vm.runInContext(code,context);assert.equal((await context.readSavedInput('job',false)).request.width,768);
 const valid=contextFor(Promise.resolve({ok:true,json:async()=>({id:'job',request})}),()=>1);
 vm.runInContext(code,valid);assert.equal((await valid.readSavedInput('job')).restoredFile.size,1);
});
test('MiniMax 저장 입력은 요청과 본문 읽기 지연에서 시간 초과 후 대기를 해제한다',async()=>{
 for(const stage of ['request','json']){
  let timer;const delayed=new Promise(()=>{});
  const context=contextFor(stage==='request'?delayed:Promise.resolve({ok:true,json:()=>delayed}),fn=>(timer=fn,1));
  vm.runInContext(code,context);const waiting=context.readSavedInput('job');await new Promise(resolve=>setImmediate(resolve));timer();
  await assert.rejects(waiting,/시간이 초과/);
 }
});

test('MiniMax 검토 중 중복 요청과 입력 변경을 차단하고 지연 시 복구한다',async()=>{
 const review=source.slice(source.indexOf('  async function review(event)'),source.indexOf('  async function submit()'));
 for(const scenario of ['timeout','changed','success']){
  let finish,timer,calls=0,pending=null,error='',busy=false;
  const file={},current={current:{prompt:'move',seed:42,file,checking:false}};
  const context=vm.createContext({AbortController,untilAborted,document:{activeElement:{}},current,file,prompt:'move',seed:42,busy:false,pending:null,reasons:[],reviewRequest:{current:null},imageVersion:{current:0},
   referencePng:()=>{calls++;return new Promise(resolve=>finish=resolve);},setTimeout:fn=>(timer=fn,1),clearTimeout:()=>{},setBusy:value=>busy=value,setError:value=>error=value,setPending:value=>pending=value,requestAnimationFrame:()=>{},reviewRef:{current:null}});
  vm.runInContext(review,context);const first=context.review({preventDefault(){}});await context.review({preventDefault(){}});assert.equal(calls,1);
  if(scenario==='timeout')timer();else {if(scenario==='changed')current.current={...current.current,prompt:'new'};finish('png');}
  await first;assert.equal(busy,false);assert.equal(context.reviewRequest.current,null);
  if(scenario==='timeout')assert.match(error,/시간이 초과/);
  else if(scenario==='changed')assert.match(error,/입력이 바뀌/);
  else assert.equal(pending.prompt,'move');
  if(scenario!=='success')assert.equal(pending,null);
 }
});

test('MiniMax 접수는 처리 중 검토를 유지하고 중복을 막으며 시간 초과 시 이력 확인을 안내한다',async()=>{
 const submit=source.slice(source.indexOf('  async function submit()'),source.indexOf('  async function readSavedInput('));
 for(const scenario of ['timeout','success','invalid']){
  let timer,finish,calls=0,pending={action:'generate'},busy=false,error='',notice='',job='';
  const document={body:{},activeElement:{}};
  const context=vm.createContext({AbortController,untilAborted,validVideoJobId,document,service:'minimax-h3-i2v',hasProposal:false,proposalScope:null,pending,model:{},generationReady:()=>true,sending:{current:false},reviewRef:{current:{contains:()=>false}},formRef:{current:null},requestAnimationFrame:()=>{},
   managementCommand:()=>{calls++;return new Promise(resolve=>finish=resolve);},setTimeout:fn=>(timer=fn,1),clearTimeout:()=>{},setBusy:value=>busy=value,setError:value=>error=value,setNotice:value=>notice=value,setPending:value=>pending=value,setJob:value=>job=value,setRevision:()=>{}});
  vm.runInContext(submit,context);const first=context.submit();await context.submit();assert.equal(calls,1);assert.equal(busy,true);assert.notEqual(pending,null);
  if(scenario==='timeout')timer();else finish(scenario==='success'?{id:'2026-11-24_12-00-00-1234abcd'}:{id:'잘못된-ID'});
  await first;assert.equal(busy,false);assert.equal(pending,null);assert.equal(context.sending.current,false);
  if(scenario==='success'){assert.equal(job,'2026-11-24_12-00-00-1234abcd');assert.match(notice,/접수했습니다/);}else assert.match(error,/접수 여부가 불확실.*이력/);
 }
});

test('MiniMax 정책 조회는 요청과 본문 지연을 종료하고 화면 종료 후 늦은 응답을 무시한다',async()=>{
 const effect=source.slice(source.indexOf('  useEffect(()=>{\n    let active=true,timedOut=false;'),source.indexOf('  const [prompt,setPrompt]'));
 for(const stage of ['request','json','cleanup']){
  let timer,cleanup,resolve,policy='initial';
  const delayed=new Promise(done=>resolve=done),response={ok:true,json:()=>stage==='json'?delayed:Promise.resolve({minimax_preferred:true})};
  const context=vm.createContext({AbortController,untilAborted,policyRevision:0,useEffect:fn=>cleanup=fn(),setTimeout:fn=>(timer=fn,1),clearTimeout:()=>{},setPolicy:value=>policy=value,fetch:()=>stage==='json'?Promise.resolve(response):delayed});
  vm.runInContext(effect,context);await new Promise(done=>setImmediate(done));
  if(stage==='cleanup'){cleanup();resolve(response);}else {timer();resolve(stage==='json'?{minimax_preferred:true}:response);}
  await new Promise(done=>setImmediate(done));assert.equal(policy,stage==='cleanup'?null:'timeout');
 }
});

test('MiniMax 검토가 열릴 때 사용자가 옮긴 초점은 유지한다',async()=>{
 const review=source.slice(source.indexOf('  async function review(event)'),source.indexOf('  async function submit()'));
 for(const moved of [false,true]){
  const origin={},other={},body={},file={};let frame,focused=0;
  const document={activeElement:origin,body};
  const context=vm.createContext({AbortController,untilAborted,document,file,prompt:'move',seed:42,busy:false,pending:null,reasons:[],reviewRequest:{current:null},imageVersion:{current:0},current:{current:{prompt:'move',seed:42,file,checking:false}},referencePng:async()=> 'png',setTimeout:()=>1,clearTimeout:()=>{},setBusy:()=>{},setError:()=>{},setPending:()=>{},requestAnimationFrame:fn=>frame=fn,reviewRef:{current:{focus:()=>focused++}}});
  vm.runInContext(review,context);await context.review({preventDefault(){}});document.activeElement=moved?other:body;frame();assert.equal(focused,moved?0:1);
 }
});

test('MiniMax 검토 취소는 사라진 초점만 입력 영역으로 복구한다',()=>{
 const code=source.slice(source.indexOf('  function cancelReview()'),source.indexOf('  return <article'));
 for(const moved of [false,true]){
  const body={},close={},other={};let frame,focused=0,pending=true;const document={body,activeElement:close};
  const context=vm.createContext({document,restoreLostFocus,visibleFocusTarget,reviewRef:{current:{contains:node=>node===close}},formRef:{current:{isConnected:true,focus:()=>focused++}},setPending:value=>pending=value,requestAnimationFrame:fn=>frame=fn});
  vm.runInContext(code,context);context.cancelReview();document.activeElement=moved?other:body;frame();assert.equal(pending,null);assert.equal(focused,moved?0:1);
 }
});

test('MiniMax 영상 검토 취소는 접힌 입력 카드의 제목으로 초점을 복구한다',()=>{
 for(const file of ['MiniMaxH3Page.jsx','MiniMaxH3Ref2VAPage.jsx']){
  const source=readFileSync(new URL('../../gui/'+file,import.meta.url),'utf8');
  const start=source.indexOf('  function cancelReview()'),end=source.indexOf('\n  }',start);
  let frame,focused='';const body={},close={},document={body,activeElement:close};
  const summary={isConnected:true,focus:()=>focused='summary'};
  const form={isConnected:true,focus:()=>focused='form',parentElement:{tagName:'DETAILS',open:false,querySelector:()=>summary}};
  const context=vm.createContext({document,restoreLostFocus,visibleFocusTarget,reviewRef:{current:{contains:node=>node===close}},formRef:{current:form},setPending:()=>{},requestAnimationFrame:fn=>frame=fn});
  vm.runInContext(source.slice(start,end+4),context);context.cancelReview();document.activeElement=body;frame();assert.equal(focused,'summary',file);
 }
});

test('MiniMax 저장 입력 적용은 조회 중 이동한 초점을 빼앗지 않는다',()=>{
 const code=source.slice(source.indexOf('  function restoreSavedInput('),source.indexOf('  function cancelReview()'));
 for(const moved of [false,true]){
  const body={},origin={},other={},file={};let frame,focused=0;const document={body,activeElement:origin};
  const start={busy:false,pending:null,checking:false,prompt:'old',seed:1,file};
  const context=vm.createContext({document,current:{current:start},reviewRequest:{current:null},imageVersion:{current:0},promptEdited:{current:false},inputRef:{current:{open:false}},formRef:{current:{focus:()=>focused++}},requestAnimationFrame:fn=>frame=fn,setPrompt:()=>{},setSeed:()=>{},setFile:()=>{},setNotice:()=>{},setError:()=>{}});
  vm.runInContext(code,context);context.restoreSavedInput({prompt:'new',seed:42},{id:'job',inputAtStart:start,version:0,focusAtStart:origin,restoredFile:{}});
  document.activeElement=moved?other:origin;frame();assert.equal(focused,moved?0:1);assert.equal(context.inputRef.current.open,true);
 }
});

test('MiniMax 제안이 늦게 도착해도 사용자가 수정 후 비운 프롬프트를 채우지 않는다',async()=>{
 const effect=source.match(/useEffect\(\(\)=>\{let active=true;\(async\(\)=>\{try\{const scope=generationProposalScope.*?\},\[session\]\);/)[0];
 for(const edited of [false,true]){
  let finish,prompt='',cleanup;
  const context=vm.createContext({useEffect:fn=>cleanup=fn(),location:{search:''},session:'session',service:'minimax-h3-i2v',promptEdited:{current:edited},generationProposalScope:()=>({}),managementCommand:()=>{},readGenerationProposal:()=>new Promise(resolve=>finish=resolve),setPrompt:fn=>prompt=fn(prompt),setProposalScope:()=>{},setError:()=>{}});
  vm.runInContext(effect,context);finish({service:'minimax-h3-i2v',mode:'first_frame',prompt:'제안'});await new Promise(done=>setImmediate(done));
  assert.equal(prompt,edited?'':'제안');cleanup();
 }
});

test('대화 영상 제안은 고정 접수 ID로 위임하고 결과를 확인한다',async()=>{
 const submit=source.slice(source.indexOf('  async function submit()'),source.indexOf('  async function readSavedInput('));
 const proposalScope={session:'a'.repeat(32),job:'2026-11-24_10-00-00-12345678',kind:'video'};
 let captured,job='',refresh=0;const receipt={state:'editing',id:'flux_'+ '1'.repeat(64),refresh:()=>refresh++,unknown:()=>{throw Error('unexpected')}};
 const document={body:{},activeElement:{}};
 const context=vm.createContext({AbortController,untilAborted,validVideoJobId,document,service:'minimax-h3-i2v',hasProposal:true,proposalScope,receipt,readGenerationProposal:async()=>({}),pending:{action:'generate'},model:{},generationReady:()=>true,sending:{current:false},reviewRef:{current:{contains:()=>false}},formRef:{current:null},requestAnimationFrame:()=>{},managementCommand:async(...args)=>{captured=args;return {state:'accepted',job_id:'2026-11-24_12-00-00-12345678'};},setTimeout:()=>1,clearTimeout:()=>{},setBusy:()=>{},setError:()=>{},setNotice:()=>{},setPending:()=>{},setJob:value=>job=value,setRevision:()=>{}});
 vm.runInContext(submit,context);await context.submit();
 assert.equal(captured[0],'hermes-agent');assert.equal(captured[1],'hermes-minimax-submit');assert.equal(captured[2].request_id,receipt.id);assert.equal(captured[2].session_id,proposalScope.session);assert.equal(job,'2026-11-24_12-00-00-12345678');assert.equal(refresh,1);
});
