import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import vm from 'node:vm';
import {untilAborted} from '../../gui/managementCommand.js';
import {requestErrorMessage} from '../../gui/requestError.mjs';
import {restoreLostFocus} from '../../gui/restoreLostFocus.mjs';

test('VACE 검토 지연은 중복을 막고 시간 초과 후 재시도한다',async()=>{
 const source=readFileSync(new URL('../../gui/VacePage.jsx',import.meta.url),'utf8');
 const code=source.slice(source.indexOf('  async function review(event)'),source.indexOf('  async function submit()',source.indexOf('  async function review(event)')));
 for(const stage of ['image','video','handoff']){
  let timeout,busy=false,error='',pending=null,calls=0,slow=true;const reviewRequest={current:null};
  const wait=()=>new Promise(()=>{}),context=vm.createContext({AbortController,untilAborted,requestErrorMessage,reviewRequest,reviewOrigin:{current:null},document:{activeElement:{}},interactionRef:{current:{busy:false,pending:null}},imageChecking:{current:false},videoControllers:{current:{}},reviewEpoch:{current:0},values:{mode:'pose'},files:{reference:{},pose_video:{}},attachments:['pose_video'],setTimeout:fn=>(timeout=fn,1),clearTimeout:()=>{},setBusy:value=>busy=value,setError:value=>error=value,setPending:value=>pending=value,referencePng:()=>slow && stage==='image'?wait():Promise.resolve('png'),videoData:()=>slow && stage==='video'?wait():Promise.resolve('video'),handoff:{preview:()=>{calls++;return slow && stage==='handoff'?wait():Promise.resolve();},clearReview:()=>{}}});
  vm.runInContext(code,context);const event={preventDefault(){}};const first=context.review(event);await context.review(event);await new Promise(resolve=>setImmediate(resolve));timeout();await first;
  assert.match(error,/시간이 초과/);assert.equal(busy,false);assert.equal(pending,null);assert.equal(reviewRequest.current,null);assert.equal(calls,stage==='handoff'?1:0);
  slow=false;await context.review(event);assert.equal(error,'');assert.equal(busy,false);assert.equal(pending.pose_video,'video');
 }
});

test('VACE 검토 오류는 사용자가 옮긴 초점을 유지한다',()=>{
 const source=readFileSync(new URL('../../gui/VacePage.jsx',import.meta.url),'utf8');
 const effect=source.match(/useEffect\(\(\)=>\{if\(busy \|\| pending \|\| !error \|\| !reviewOrigin\.current\).*?\},\[busy,pending,error\]\);/s)?.[0];assert.ok(effect);
 for(const moved of [false,true]){
  let run,frame,focused=0;const body={},button={isConnected:true,focus:()=>focused++},document={body,activeElement:moved?{}:body};
  const context=vm.createContext({busy:false,pending:null,error:'오류',reviewOrigin:{current:button},document,restoreLostFocus,visibleFocusTarget:value=>value,useEffect:fn=>run=fn,requestAnimationFrame:fn=>(frame=fn,1),cancelAnimationFrame:()=>{}});
  vm.runInContext(effect,context);run();frame();assert.equal(focused,moved?0:1);
 }
});

test('VACE 검토 중 화면 종료 후 늦은 응답은 결과를 열지 않는다',async()=>{
 const source=readFileSync(new URL('../../gui/VacePage.jsx',import.meta.url),'utf8');
 const code=source.slice(source.indexOf('  async function review(event)'),source.indexOf('  async function submit()',source.indexOf('  async function review(event)')));
 let resolve,updates=0;const reviewRequest={current:null};
 const context=vm.createContext({AbortController,untilAborted,requestErrorMessage,reviewRequest,reviewOrigin:{current:null},document:{activeElement:{}},interactionRef:{current:{busy:false,pending:null}},imageChecking:{current:false},videoControllers:{current:{}},reviewEpoch:{current:0},values:{mode:'text'},files:{},attachments:[],setTimeout,clearTimeout,setBusy:()=>updates++,setError:()=>updates++,setPending:()=>updates++,handoff:{preview:()=>new Promise(done=>resolve=done),clearReview:()=>{}}});
 vm.runInContext(code,context);const pending=context.review({preventDefault(){}});await new Promise(done=>setImmediate(done));const before=updates,controller=reviewRequest.current;reviewRequest.current=null;controller.abort();await pending;resolve();await Promise.resolve();assert.equal(updates,before);
});
