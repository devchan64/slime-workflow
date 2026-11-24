import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import vm from 'node:vm';
import {untilAborted} from '../../gui/managementCommand.js';
import {requestErrorMessage} from '../../gui/requestError.mjs';
import {restoreLostFocus} from '../../gui/restoreLostFocus.mjs';
import {verifyKimodoProposal} from '../../gui/kimodoProposalMembership.mjs';
import {kimodoPromptReason} from '../../gui/kimodoPromptReason.mjs';

test('Kimodo 동작 설명의 입력 제한과 해결 사유를 구분한다',()=>{
 for(const [prompt,expected] of [['  ','입력'],['! 🚶','문자 또는 숫자'],[Array(101).fill('walk').join(' '),'100단어'],[Array(100).fill('걷기').join(' '),'']]){
  const result=kimodoPromptReason(prompt);assert.equal(expected ? result.includes(expected) : result==='',true);
 }
});

test('Kimodo 초기 제안의 손상 응답 후 정상 재조회가 가능하다',async()=>{
 const source=readFileSync(new URL('../../gui/KimodoProposal.jsx',import.meta.url),'utf8');
 const code=source.slice(source.indexOf('  async function load()'),source.indexOf('  if(!proposal)return',source.indexOf('  async function load()')));
 const session='a'.repeat(32),job='2026-11-18_00-00-00-12345678',snapshot='b'.repeat(64),page={id:session,offset:0,snapshot,messages:[{job_id:job,session_job_unique:true,job:{status:{status:'completed'},final_response:'HERMES_KIMODO_PROPOSAL'}}]};
 let current={},error='',busy=false,shown=null;const request={current:null},selection={current:'scope'};
 const command=async(_service,name)=>name==='hermes-session-view'?page:{job_id:job,proposal:current};
 const context=vm.createContext({AbortController,request,selection,focusOnError:{current:false},loadFocus:{current:false},loadRef:{current:null},document:{activeElement:null},session,job,snapshot,offset:0,verifyKimodoProposal,requestErrorMessage,setTimeout:()=>1,clearTimeout:()=>{},setBusy:v=>busy=v,setError:v=>error=v,setOriginal:()=>{},setProposal:v=>shown=v,readProposalPreview:(verify,args)=>verify(command,...args)});
 vm.runInContext(code,context);await context.load();assert.match(error,/확인할 수 없습니다/);assert.equal(shown,null);assert.equal(busy,false);assert.equal(request.current,null);
 current={prompt:'walk',frames:30,steps:2,seed:1};await context.load();assert.equal(error,'');assert.deepEqual(shown,current);assert.equal(busy,false);assert.equal(request.current,null);
});

test('Kimodo 제안 확인 중 종료하면 늦은 응답으로 입력을 추가하지 않는다',async()=>{
 const source=readFileSync(new URL('../../gui/KimodoProposal.jsx',import.meta.url),'utf8');
 const code=source.slice(source.indexOf('  async function addRequest(event)'),source.indexOf('  return <form',source.indexOf('  async function addRequest(event)')));
 let resolve,added=0,fetches=0,updates=0;const request={current:null};
 const context=vm.createContext({AbortController,DOMException,promptReason:"",request,selection:{current:"initial"},focusOnError:{current:false},document:{activeElement:null},untilAborted,requestErrorMessage,job:'j',session:'s',snapshot:'h',offset:0,original:{},proposal:{prompt:'p',frames:30,steps:2,seed:1},setTimeout:()=>1,clearTimeout:()=>{},setBusy:()=>updates++,setError:()=>updates++,managementCommand:()=>{},verifyKimodoProposal:()=>new Promise(done=>resolve=done),fetch:()=>fetches++,append:()=>added++,openStep:()=>added++});
 vm.runInContext(code,context);const event={nativeEvent:{submitter:{value:'workflow'}},preventDefault:()=>{}};const pending=context.addRequest(event);await context.addRequest(event);const controller=request.current;request.current=null;controller.abort();const before=updates;resolve();await pending;assert.equal(fetches,0);assert.equal(added,0);assert.equal(updates,before);
});

test('대화 이력 변경 직후 이전 Kimodo 확인 결과를 적용하지 않는다',async()=>{
 const source=readFileSync(new URL('../../gui/KimodoProposal.jsx',import.meta.url),'utf8');
 const code=source.slice(source.indexOf('  async function addRequest(event)'),source.indexOf('  return <form',source.indexOf('  async function addRequest(event)')));
 let resolve,error='',added=0,fetches=0;const request={current:null},selection={current:'old'};
 const context=vm.createContext({AbortController,DOMException,promptReason:"",request,selection,focusOnError:{current:false},document:{activeElement:null},untilAborted,requestErrorMessage,job:'j',session:'s',snapshot:'old',offset:0,original:{},proposal:{prompt:'p',frames:30,steps:2,seed:1},setTimeout:()=>1,clearTimeout:()=>{},setBusy:()=>{},setError:value=>error=value,managementCommand:()=>{},verifyKimodoProposal:()=>new Promise(done=>resolve=done),fetch:()=>fetches++,append:()=>added++,openStep:()=>added++});
 vm.runInContext(code,context);const pending=context.addRequest({nativeEvent:{submitter:{value:'workflow'}},preventDefault:()=>{}});selection.current='new';resolve();await pending;assert.equal(fetches,0);assert.equal(added,0);assert.match(error,/이력이 변경/);assert.equal(request.current,null);
});

test('대화 이력 변경 직후 이전 요청의 오류는 이력 변경으로 안내한다',async()=>{
 const source=readFileSync(new URL('../../gui/KimodoProposal.jsx',import.meta.url),'utf8');
 const code=source.slice(source.indexOf('  async function addRequest(event)'),source.indexOf('  return <form',source.indexOf('  async function addRequest(event)')));
 let reject,error='';const request={current:null},selection={current:'old'};
 const context=vm.createContext({AbortController,DOMException,promptReason:"",request,selection,focusOnError:{current:false},document:{activeElement:null},untilAborted,requestErrorMessage,job:'j',session:'s',snapshot:'old',offset:0,original:{},proposal:{prompt:'p',frames:30,steps:2,seed:1},setTimeout:()=>1,clearTimeout:()=>{},setBusy:()=>{},setError:value=>error=value,managementCommand:()=>{},verifyKimodoProposal:()=>new Promise((_,fail)=>reject=fail),fetch:()=>{},append:()=>{},openStep:()=>{}});
 vm.runInContext(code,context);const pending=context.addRequest({nativeEvent:{submitter:{value:'workflow'}},preventDefault:()=>{}});selection.current='new';reject(new Error('이전 오류'));await pending;assert.match(error,/이력이 변경/);assert.equal(request.current,null);
});

test('Kimodo 확인 오류는 잃은 초점만 안내로 옮긴다',()=>{
 const source=readFileSync(new URL('../../gui/KimodoProposal.jsx',import.meta.url),'utf8');
 const effect=source.match(/useEffect\(\(\)=>\{if\(busy \|\| !focusOnError\.current\).*?\},\[busy,error\]\);/s)?.[0];assert.ok(effect);
 for(const moved of [false,true]){
  let run,frame,focused=0;const body={},other={},document={body,activeElement:moved?other:body};
  const context=vm.createContext({document,restoreLostFocus,busy:false,error:'오류',focusOnError:{current:true},errorRef:{current:{isConnected:true,focus:()=>focused++}},useEffect:fn=>run=fn,requestAnimationFrame:fn=>(frame=fn,1),cancelAnimationFrame:()=>{}});
  vm.runInContext(effect,context);const cleanup=run();frame();cleanup();assert.equal(focused,moved?0:1);
 }
});

test('Kimodo 초기 조회 결과는 잃은 초점만 검토 영역으로 옮긴다',()=>{
 const source=readFileSync(new URL('../../gui/KimodoProposal.jsx',import.meta.url),'utf8');
 const effect=source.match(/useEffect\(\(\)=>\{if\(busy \|\| !loadFocus\.current\).*?\},\[busy,proposal\]\);/s)?.[0];assert.ok(effect);
 for(const moved of [false,true]){
  let run,frame,focused=0;const body={},other={},document={body,activeElement:moved?other:body};
  const context=vm.createContext({document,restoreLostFocus,busy:false,proposal:{},loadFocus:{current:true},resultRef:{current:{isConnected:true,focus:()=>focused++}},useEffect:fn=>run=fn,requestAnimationFrame:fn=>(frame=fn,1),cancelAnimationFrame:()=>{}});
  vm.runInContext(effect,context);const cleanup=run();frame();cleanup();assert.equal(focused,moved?0:1);
 }
});

test('Kimodo 예제 폼 접기는 폼 안에서 잃은 초점만 복구한다',()=>{
 const source=readFileSync(new URL('../../gui/KimodoProposal.jsx',import.meta.url),'utf8');
 const start=source.indexOf('onClick={()=>{const restore=exampleOpen'),end=source.indexOf('}}>{exampleOpen?',start);assert.ok(start>=0 && end>start);
 const code=source.slice(start+'onClick={'.length,end+1);
 for(const scenario of ['lost','moved','outside','opening']){
  let frame,focused=0;const body={},inside={},other={},document={body,activeElement:scenario==='outside'?other:inside};
  const context=vm.createContext({document,restoreLostFocus,exampleOpen:scenario!=='opening',exampleRef:{current:{contains:value=>value===inside}},exampleToggleRef:{current:{isConnected:true,focus:()=>focused++}},focusFrame:{current:null},setExampleMounted:()=>{},setExampleOpen:()=>{},cancelAnimationFrame:()=>{},requestAnimationFrame:fn=>(frame=fn,1)});
  vm.runInContext('('+code+')()',context);document.activeElement=scenario==='lost'?body:other;frame?.();assert.equal(focused,scenario==='lost'?1:0,scenario);
 }
});

test('Kimodo 확인이 시간 초과된 뒤 정상 재시도할 수 있다',async()=>{
 const source=readFileSync(new URL('../../gui/KimodoProposal.jsx',import.meta.url),'utf8');
 const code=source.slice(source.indexOf('  async function addRequest(event)'),source.indexOf('  return <form',source.indexOf('  async function addRequest(event)')));
 for(const stage of ['verify','body']){
  let timeout,busy=false,error='',added=0,slow=true;const request={current:null};
  const context=vm.createContext({AbortController,DOMException,promptReason:"",request,selection:{current:"initial"},focusOnError:{current:false},document:{activeElement:null},untilAborted,requestErrorMessage,job:'j',session:'s',snapshot:'h',offset:0,original:{},proposal:{prompt:'p',frames:30,steps:2,seed:1},setTimeout:fn=>(timeout=fn,1),clearTimeout:()=>{},setBusy:value=>busy=value,setError:value=>error=value,managementCommand:()=>{},verifyKimodoProposal:()=>slow && stage==='verify'?new Promise(()=>{}):Promise.resolve(),fetch:()=>Promise.resolve({ok:true,json:()=>slow && stage==='body'?new Promise(()=>{}):Promise.resolve({request:{action:'generate',prompt:'p',frames:30,steps:2,seed:1}})}),append:()=>added++,openStep:()=>added++});
  vm.runInContext(code,context);const event={nativeEvent:{submitter:{value:'workflow'}},preventDefault:()=>{}};const pending=context.addRequest(event);await new Promise(resolve=>setImmediate(resolve));timeout();await pending;assert.match(error,/초과/);assert.equal(busy,false);assert.equal(request.current,null);assert.equal(added,0);
  slow=false;await context.addRequest(event);assert.equal(error,'');assert.equal(busy,false);assert.equal(added,1);
 }
});

test('Kimodo 확인 응답이 입력과 다르면 요청을 전달하지 않는다',async()=>{
 const source=readFileSync(new URL('../../gui/KimodoProposal.jsx',import.meta.url),'utf8');
 const code=source.slice(source.indexOf('  async function addRequest(event)'),source.indexOf('  return <form',source.indexOf('  async function addRequest(event)')));
 for(const result of [null,{}, {request:{action:'generate',prompt:'p',frames:31,steps:2,seed:1}}]){
  let added=0,error='';const request={current:null};
  const context=vm.createContext({AbortController,DOMException,promptReason:"",request,selection:{current:"initial"},focusOnError:{current:false},document:{activeElement:null},untilAborted,requestErrorMessage,job:'j',session:'s',snapshot:'h',offset:0,original:{},proposal:{prompt:'p',frames:30,steps:2,seed:1},setTimeout:()=>1,clearTimeout:()=>{},setBusy:()=>{},setError:value=>error=value,managementCommand:()=>{},verifyKimodoProposal:()=>Promise.resolve(),fetch:()=>Promise.resolve({ok:true,json:()=>Promise.resolve(result)}),append:()=>added++,openStep:()=>added++});
  vm.runInContext(code,context);await context.addRequest({nativeEvent:{submitter:{value:'workflow'}},preventDefault:()=>{}});assert.equal(added,0);assert.match(error,/일치하지 않습니다/);assert.equal(request.current,null);
 }
});
