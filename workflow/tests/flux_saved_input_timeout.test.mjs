import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import vm from 'node:vm';
import {untilAborted} from '../../gui/managementCommand.js';

test('FLUX 저장 입력의 요청과 본문 지연은 시간 초과 또는 화면 종료로 해제된다',async()=>{
 const source=readFileSync(new URL('../../gui/FluxImagePage.jsx',import.meta.url),'utf8');
 const code=source.slice(source.indexOf('  async function readJob(id,'),source.indexOf('  function restore('));
 for(const phase of ['fetch','body'])for(const cancel of [false,true]){
  let timer;const external=new AbortController();
  const context=vm.createContext({AbortController,untilAborted,document:{activeElement:null},inputRef:{current:{form:{},files:[]}},imageSelectionRevision:{current:0},checkingSlots:{current:new Set()},reviewEpoch:{current:0},service:'flux-image',setTimeout:fn=>(timer=fn,1),clearTimeout:()=>{},fetch:()=>phase==='fetch'?new Promise(()=>{}):Promise.resolve({ok:true,json:()=>new Promise(()=>{})})});
  vm.runInContext(code,context);const pending=context.readJob('job',{signal:external.signal});await Promise.resolve();
  if(cancel)external.abort();else timer();
  await assert.rejects(pending,cancel?/시간 초과 또는 화면 종료/:/조회 시간이 초과/);
 }
});

test('FLUX 저장 입력의 잘못된 JSON은 형식 재조회 안내를 표시한다',async()=>{
 const source=readFileSync(new URL('../../gui/FluxImagePage.jsx',import.meta.url),'utf8');
 const code=source.slice(source.indexOf('  async function readJob(id,'),source.indexOf('  function restore('));
 const context=vm.createContext({AbortController,untilAborted,document:{activeElement:null},inputRef:{current:{form:{},files:[]}},imageSelectionRevision:{current:0},checkingSlots:{current:new Set()},reviewEpoch:{current:0},service:'flux-image',setTimeout,clearTimeout,fetch:async()=>({ok:true,json:async()=>{throw new SyntaxError('Unexpected token');}})});
 vm.runInContext(code,context);await assert.rejects(context.readJob('job'),/저장된 입력 형식을 확인할 수 없습니다/);
});

test('FLUX 이력 입력 적용은 변경된 입력을 보호하고 이동한 초점을 유지한다',()=>{
 const source=readFileSync(new URL('../../gui/FluxImagePage.jsx',import.meta.url),'utf8');
 const code=source.slice(source.indexOf('  function restore(input,record)'),source.indexOf('  function edit('));
 for(const changed of [false,true])for(const moved of [false,true])for(const newReview of [false,true]){
  let frame,focused=0,applied=0;const body={},origin={},other={},document={body,activeElement:origin},state={form:{},files:[]},card={open:false};
  const context=vm.createContext({document,reviewEpoch:{current:0},interactionRef:{current:{busy:false,review:null}},checkingSlots:{current:new Set()},inputRef:{current:state},imageSelectionRevision:{current:changed?1:0},seamless:false,setForm:()=>applied++,setFiles:()=>{},setReferenceReset:()=>{},setNotice:()=>{},inputFormRef:{current:{isConnected:true,closest:()=>card,focus:()=>focused++}},requestAnimationFrame:fn=>frame=fn});
  const record={reviewAtStart:0,checkingAtStart:false,inputAtStart:state,imageAtStart:0,files:[],focusAtStart:origin};
  vm.runInContext(code,context);if(changed){assert.throws(()=>context.restore({},record),/변경/);assert.equal(applied,0);continue;}
  context.restore({},record);assert.equal(card.open,true);document.activeElement=moved?other:body;if(newReview)context.reviewEpoch.current++;frame();assert.equal(applied,1);assert.equal(focused,moved || newReview?0:1);
 }
});
