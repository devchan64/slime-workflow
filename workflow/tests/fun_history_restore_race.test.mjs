import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import vm from 'node:vm';
import {untilAborted} from '../../gui/managementCommand.js';
import {visibleFocusTarget} from '../../gui/restoreLostFocus.mjs';

const source=readFileSync(new URL('../../gui/FunControlPage.jsx',import.meta.url),'utf8');
const code=source.slice(source.indexOf('  async function readJob('),source.indexOf('  function cleaned('));
test('이미지 확인 중 포즈 선택은 렌더 전에도 시작하지 않는다',async()=>{
 const attach=source.slice(source.indexOf('  async function attach(file,field)'),source.indexOf('  async function load('));
 let error='',calls=0;
 const context=vm.createContext({imageChecking:{current:true},setPoseError:value=>error=value,videoData:()=>{calls++;}});
 vm.runInContext(attach+'\nthis.attach=attach;',context);
 assert.equal(await context.attach({name:'pose.mp4'},'pose_video'),false);
 assert.match(error,/이미지 확인이 끝난 뒤/);assert.equal(calls,0);
});
test('다른 첨부 처리 중 포즈 선택은 새 처리를 시작하지 않는다',async()=>{
 const attach=source.slice(source.indexOf('  async function attach(file,field)'),source.indexOf('  async function load('));
 let error='',calls=0;
 const context=vm.createContext({imageChecking:{current:false},attachmentProcessing:{current:true},setPoseError:value=>error=value,videoData:()=>{calls++;}});
 vm.runInContext(attach+'\nthis.attach=attach;',context);
 assert.equal(await context.attach({name:'pose.mp4'},'pose_video'),false);
 assert.match(error,/첨부 처리가 끝난 뒤/);assert.equal(calls,0);
});
function fixture(fetch){
 const body={},origin={},other={},frames=[];let focused=0;
 const context=vm.createContext({AbortController,untilAborted,setTimeout,clearTimeout,encodeURIComponent,fetch,validFunInput:()=>true,document:{body,activeElement:origin},requestRef:{current:{prompt:'기존'}},attachmentRevision:{current:0},imageChecking:{current:false},attachmentProcessing:{current:false},reviewEpoch:{current:0},interactionRef:{current:{busy:false,pending:null}},restoreFrame:{current:null},formRef:{current:{isConnected:true,focus:()=>focused++}},setRequest:value=>context.requestRef.current=value,setReferenceReset:()=>{},setVideoInfo:()=>{},setPoseError:()=>{},setError:()=>{},poseError:"",setSourceSeed:()=>{},setSourceJob:()=>{},setNotice:()=>{},requestAnimationFrame:fn=>(frames.push(fn),frames.length),cancelAnimationFrame:()=>{}});
 vm.runInContext(code+'\nthis.readJob=readJob;this.readHistoryInput=readHistoryInput;this.restore=restore;',context);return {context,body,origin,other,frames,focused:()=>focused};
}
test('포즈 미리보기 경로와 실제 복원 첨부는 서로 구분된다',async()=>{
 const id='2026-11-18_00-00-00-12345678',original='saved-base64-pose',images=['saved-image'];
 const f=fixture(async()=>({ok:true,json:async()=>({id,request:{prompt:'복원',seed:1,images,pose_video:original},video:{}})}));
 const record=await f.context.readHistoryInput(id);
 assert.equal(record.request.pose_video,'/management/assistant/fun-pose/'+id);
 assert.equal(record.attachments.pose_video,original);
 f.context.restore(record.request,record);
 assert.equal(f.context.requestRef.current.pose_video,original);
 assert.deepEqual(f.context.requestRef.current.images,images);
});
test('Fun Control 이력 조회는 본문 읽기 중에도 상위 중단을 따른다',async()=>{
 for(const stage of ['fetch','body']){
  const f=fixture(()=>stage==='fetch'?new Promise(()=>{}):Promise.resolve({ok:true,json:()=>new Promise(()=>{})})),controller=new AbortController();
  const pending=f.context.readJob('id',{signal:controller.signal});await Promise.resolve();controller.abort();await assert.rejects(pending,{name:'AbortError'});
 }
});
test('Fun Control 입력 수정 직후 렌더 전에도 늦은 이력 복원을 거부한다',()=>{
 const f=fixture(()=>{}),c=f.context,record={id:'id',inputAtStart:c.requestRef.current,attachmentAtStart:0,checkingAtStart:false,reviewAtStart:0,focusAtStart:f.origin,attachments:{}};
 const setter=source.match(/  function setRequest\(value\)\{.*?\}/)?.[0];assert.ok(setter);c.setRequestState=()=>{};vm.runInContext(setter+'\nthis.editRequest=setRequest;',c);
 c.editRequest({...c.requestRef.current,prompt:'새 입력'});assert.throws(()=>c.restore({prompt:'이력',seed:1},record),/입력이 변경/);assert.equal(c.requestRef.current.prompt,'새 입력');
});
test('Fun Control 연속 복원은 첫 입력을 지키고 초점 이동과 새 검토를 존중한다',()=>{
 for(const mode of ['unchanged','moved','review']){
  const f=fixture(()=>{}),c=f.context,record={id:'id',inputAtStart:c.requestRef.current,attachmentAtStart:0,checkingAtStart:false,reviewAtStart:0,focusAtStart:f.origin,attachments:{images:[],pose_video:''}};
  c.restore({prompt:'복원',seed:1},record);assert.throws(()=>c.restore({prompt:'늦음',seed:1},record),/입력이 변경/);
  if(mode==='moved')c.document.activeElement=f.other;if(mode==='review')c.reviewEpoch.current++;f.frames[0]();assert.equal(f.focused(),mode==='unchanged'?1:0);
 }
});
test('이력 입력 적용은 이전 포즈 오류를 지우되 다른 오류는 보존한다',()=>{
 for(const prior of ['포즈 오류','다른 오류']){
  const f=fixture(()=>{}),c=f.context;let shown=prior,pose='포즈 오류';
  c.poseError=pose;c.setPoseError=value=>pose=value;c.setError=update=>shown=update(shown);
  c.restore({prompt:'복원',seed:1},{id:'id',inputAtStart:c.requestRef.current,attachmentAtStart:0,checkingAtStart:false,reviewAtStart:0,focusAtStart:f.origin,attachments:{images:[],pose_video:''}});
  assert.equal(pose,'');assert.equal(shown,prior==='포즈 오류'?'':prior);
 }
});
test('Fun Control 검토는 렌더 전 변경된 최신 입력을 사용한다',async()=>{
 const review=source.slice(source.indexOf('  async function review(event){'),source.indexOf('  function renderResult('));let pending;
 const context=vm.createContext({AbortController,setTimeout,clearTimeout,document:{activeElement:{}},reviewOrigin:{current:null},reviewRequest:{current:null},interactionRef:{current:{busy:false,pending:null}},imageChecking:{current:false},attachmentProcessing:{current:false},attachmentRevision:{current:0},reviewEpoch:{current:0},requestRef:{current:{prompt:'최신',frames:'21'}},settings:[['frames']],embedded:false,session:'',setBusy:()=>{},setError:()=>{},setHandoffReview:()=>{},setPending:value=>pending=value});
 vm.runInContext(review+'\nthis.review=review;',context);await context.review({preventDefault:()=>{}});assert.equal(pending.prompt,'최신');assert.equal(pending.frames,21);
});
test('Fun Control 검토는 중복과 지연을 처리하고 입력 변경 시 양도 조회를 시작하지 않는다',async()=>{
 const code=source.slice(source.indexOf('  async function review(event){'),source.indexOf('  function renderResult('));
 for(const mode of ['timeout','changed','unmount']){
  let finish,timer,calls=0,error='',pending;const c=vm.createContext({AbortController,untilAborted,setTimeout:fn=>(timer=fn,1),clearTimeout:()=>{},document:{activeElement:{}},reviewOrigin:{current:null},reviewRequest:{current:null},interactionRef:{current:{busy:false,pending:null}},imageChecking:{current:false},attachmentProcessing:{current:false},attachmentRevision:{current:0},reviewEpoch:{current:0},requestRef:{current:{prompt:'원본',frames:'21'}},settings:[['frames']],embedded:true,session:'s',service:'wan22-fun-control',setBusy:()=>{},setError:value=>error=value,setHandoffReview:()=>{},setPending:value=>pending=value,requestErrorMessage:problem=>problem.message,managementCommand:()=>{calls++;return new Promise(done=>finish=done);}});
  vm.runInContext(code+'\nthis.review=review;',c);const first=c.review({preventDefault:()=>{}});await c.review({preventDefault:()=>{}});assert.equal(calls,1);
  if(mode==='timeout')timer();else if(mode==='changed'){c.requestRef.current={prompt:'새 입력'};finish({session_id:'s',resident_id:'r',resident:{state:'ready'}});}else {const controller=c.reviewRequest.current;c.reviewRequest.current=null;controller.abort();finish({session_id:'s',resident_id:'r',resident:{state:'ready'}});}
  await first;assert.equal(calls,1);assert.equal(pending,undefined);if(mode==='timeout')assert.match(error,/시간이 초과/);if(mode==='changed')assert.match(error,/입력이 변경/);
 }
});
test('Fun Control 검토 열기는 사용자가 옮긴 초점을 유지한다',()=>{
 const effect=source.match(/useEffect\(\(\)=>\{if\(!pending\)return;const origin=reviewOrigin\.current;.*?\},\[pending\]\);/)?.[0];assert.ok(effect);
 for(const moved of [false,true]){const body={},origin={},other={};let run,focused=0;
  const c=vm.createContext({useEffect:fn=>run=fn,pending:{},document:{body,activeElement:moved?other:origin},reviewOrigin:{current:origin},reviewRef:{current:{focus:()=>focused++}}});vm.runInContext(effect,c);run();assert.equal(focused,moved?0:1);
 }
});
test('Fun Control 검토 취소는 새 검토와 사용자 이동 및 잠긴 입력을 존중한다',()=>{
 const code=source.slice(source.indexOf('  function cancelReview(){'),source.indexOf('  function renderResult('));
 for(const mode of ['lost','moved','review','disabled']){
  const body={},inside={},other={};let frame,focused=0;const target={isConnected:true,disabled:false,matches:()=>mode==='disabled',focus:()=>focused++};
  const c=vm.createContext({document:{body,activeElement:inside},reviewRef:{current:{contains:node=>node===inside}},reviewEpoch:{current:1},reviewRequest:{current:null},restoreFrame:{current:null},formRef:{current:{querySelector:()=>target}},setPending:()=>{},setHandoffReview:()=>{},requestAnimationFrame:fn=>(frame=fn,1),cancelAnimationFrame:()=>{},visibleFocusTarget,restoreLostFocus:(doc,node)=>{if(doc.activeElement===doc.body && node.isConnected && !node.disabled)node.focus();}});
  vm.runInContext(code+'\nthis.cancelReview=cancelReview;',c);c.cancelReview();c.document.activeElement=mode==='moved'?other:body;if(mode==='review')c.reviewEpoch.current++;frame();assert.equal(focused,mode==='lost'?1:0);
 }
});
test('Fun Control 양도 조회 중 입력이 바뀌면 이전 검토를 표시하지 않는다',async()=>{
 const code=source.slice(source.indexOf('  async function review(event){'),source.indexOf('  function renderResult('));let finish,calls=0,error='',pending,handoff;
 const c=vm.createContext({AbortController,untilAborted,setTimeout,clearTimeout,document:{activeElement:{}},reviewOrigin:{current:null},reviewRequest:{current:null},interactionRef:{current:{busy:false,pending:null}},imageChecking:{current:false},attachmentProcessing:{current:false},attachmentRevision:{current:0},reviewEpoch:{current:0},requestRef:{current:{prompt:'원본',frames:'21'}},settings:[['frames']],embedded:true,session:'s',service:'wan22-fun-control',setBusy:()=>{},setError:value=>error=value,setHandoffReview:value=>handoff=value,setPending:value=>pending=value,requestErrorMessage:problem=>problem.message,managementCommand:()=>++calls===1?Promise.resolve({session_id:'s',resident_id:'r',resident:{state:'ready'}}):new Promise(done=>finish=done)});
 vm.runInContext(code+'\nthis.review=review;',c);const promise=c.review({preventDefault:()=>{}});for(let i=0;i<10 && !finish;i++)await Promise.resolve();assert.equal(calls,2);c.requestRef.current={prompt:'새 입력'};finish({session_id:'s',resident_id:'r',service:'wan22-fun-control',review_hash:'a'.repeat(64)});await promise;
 assert.equal(pending,undefined);assert.equal(handoff,null);assert.match(error,/입력이 변경/);
});
