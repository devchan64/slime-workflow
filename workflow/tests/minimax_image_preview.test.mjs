import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import vm from 'node:vm';
import {untilAborted} from '../../gui/managementCommand.js';
import {validGenerationJobId} from '../../gui/generationJobId.mjs';
import {requestErrorMessage} from '../../gui/requestError.mjs';

test('MiniMax 이미지 검토는 시간 초과 후 입력을 유지하고 늦은 응답을 무시한다',async()=>{
 const source=readFileSync(new URL('../../gui/MiniMaxH3ImagePage.jsx',import.meta.url),'utf8');
 const code=source.slice(source.indexOf('  async function review(event)'),source.indexOf('  function closeReview()'));
 let timeout,finish,error='',busy=false,pending=null,calls=0;const sending={current:false},previewRequest={current:null};
 const context=vm.createContext({AbortController,untilAborted,requestErrorMessage,proposalScope:null,document:{activeElement:{}},previewFocus:{current:null},inputRevision:{current:0},sending,previewRequest,busy:false,pending:null,model:{generation_ready:true},prompt:'원래 입력',seed:42,size:512,downscale:false,sampler:'euler',service:'service',checking:[false,false],references:['reference'],imageBase64:async value=>value,setBusy:value=>busy=value,setError:value=>error=value,setPending:value=>pending=value,setPreview:()=>{},setTimeout:fn=>(timeout=fn,1),clearTimeout:()=>{},managementCommand:(_service,_command,request)=>{calls++;assert.equal(request.width,512);assert.equal(request.height,512);assert.equal(request.images[0],'reference');return new Promise(resolve=>finish=resolve);}});
 vm.runInContext(code,context);const task=context.review({preventDefault(){}});await context.review({preventDefault(){}});await new Promise(done=>setImmediate(done));assert.equal(calls,1);
 timeout();await task;assert.match(error,/시간이 초과/);assert.equal(busy,false);assert.equal(sending.current,false);assert.equal(pending,null);
 finish({prompt:'늦은 결과',prompt_sha256:'a'.repeat(64)});await new Promise(done=>setImmediate(done));assert.equal(pending,null);
});

test('MiniMax 이미지 접수는 중복을 막고 불확실한 응답에 이력 확인을 안내한다',async()=>{
 const source=readFileSync(new URL('../../gui/MiniMaxH3ImagePage.jsx',import.meta.url),'utf8');
 const code=source.slice(source.indexOf('  async function submit()'),source.indexOf('  return <article'));
 for(const mode of ['timeout','invalid','network','success']){
  let timeout,finish,fail,error='',busy=false,job='',pending={prompt:'입력'},calls=0;
  const sending={current:false},submissionRequest={current:null};
  const context=vm.createContext({AbortController,untilAborted,validGenerationJobId,requestErrorMessage,proposalScope:null,sending,submissionRequest,modelStatus:{current:{generation_ready:true}},pending,service:'service',setBusy:value=>busy=value,setError:value=>error=value,setJob:value=>job=value,setRevision:()=>{},setPending:value=>pending=value,setTimeout:fn=>(timeout=fn,1),clearTimeout:()=>{},managementCommand:()=>{calls++;return new Promise((resolve,reject)=>{finish=resolve;fail=reject;});}});
  vm.runInContext(code,context);const task=context.submit();await context.submit();assert.equal(calls,1);assert.equal(busy,true);
  if(mode==='timeout')timeout();else if(mode==='network')fail(new TypeError('Failed to fetch'));else finish({id:mode==='invalid'?'bad-id':'2026-11-24_12-34-56-1234abcd'});
  await task;assert.equal(busy,false);assert.equal(sending.current,false);
  if(mode==='success'){assert.equal(job,'2026-11-24_12-34-56-1234abcd');assert.equal(pending,null);}else{assert.match(error,/접수 여부가 불확실/);assert.match(error,/이력/);if(mode==='network')assert.match(error,/연결 상태를 확인/);assert.ok(pending);}
 }
});

test('MiniMax 이미지 검토 후 모델 준비가 해제되면 접수하지 않는다',async()=>{
 const source=readFileSync(new URL('../../gui/MiniMaxH3ImagePage.jsx',import.meta.url),'utf8');
 const code=source.slice(source.indexOf('  async function submit()'),source.indexOf('  return <article'));
 let calls=0;const context=vm.createContext({pending:{prompt:'입력'},sending:{current:false},modelStatus:{current:{generation_ready:false}},managementCommand:()=>calls++});
 vm.runInContext(code,context);await context.submit();assert.equal(calls,0);
});

test('대화 이미지 제안은 고정 접수 ID로 위임하고 결과를 확인한다',async()=>{
 const source=readFileSync(new URL('../../gui/MiniMaxH3ImagePage.jsx',import.meta.url),'utf8');
 const code=source.slice(source.indexOf('  async function submit()'),source.indexOf('  return <article'));
 const scope={session:'a'.repeat(32),job:'2026-11-24_10-00-00-12345678',proposal:{service:'minimax-h3-image'}};
 let captured,job='',refresh=0;const receipt={state:'editing',id:'flux_'+ '1'.repeat(64),refresh:()=>refresh++,unknown:()=>{throw Error('unexpected')}};
 const context=vm.createContext({AbortController,untilAborted,validGenerationJobId,proposalScope:scope,receipt,verifyFluxProposal:async()=>{},sending:{current:false},submissionRequest:{current:null},modelStatus:{current:{generation_ready:true}},pending:{prompt:'house'},service:'minimax-h3-image',setBusy:()=>{},setError:()=>{},setJob:value=>job=value,setRevision:()=>{},setPending:()=>{},setTimeout:()=>1,clearTimeout:()=>{},managementCommand:async(...args)=>{captured=args;return {state:'accepted',job_id:'2026-11-24_12-00-00-12345678'};}});
 vm.runInContext(code,context);await context.submit();
 assert.equal(captured[0],'hermes-agent');assert.equal(captured[1],'hermes-minimax-submit');assert.equal(captured[2].request_id,receipt.id);assert.equal(captured[2].session_id,scope.session);assert.equal(job,'2026-11-24_12-00-00-12345678');assert.equal(refresh,1);
});
