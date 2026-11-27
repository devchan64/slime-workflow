import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import vm from 'node:vm';

test('VACE 이력 적용은 입력 카드를 열고 사용자의 초점 이동과 새 검토를 존중한다',()=>{
 const source=readFileSync(new URL('../../gui/VacePage.jsx',import.meta.url),'utf8');
 const code=source.slice(source.indexOf('  function restore(input,record)'),source.indexOf('  function cleaned('));
 for(const scenario of ['restore','moved','review']){
  let frame,focused=0,scrolled=0;const body={},origin={},other={},document={body,activeElement:origin},values={},files={},card={open:false};
  const context=vm.createContext({document,reviewEpoch:{current:0},interactionRef:{current:{busy:false,pending:null}},imageChecking:{current:false},videoControllers:{current:{}},videoSequences:{current:{}},imageSelectionRevision:{current:0},inputRef:{current:{values,files}},nonLoraSettings:{current:null},formRef:{current:{isConnected:true,closest:()=>card,focus:()=>focused++,scrollIntoView:()=>scrolled++}},setChecking:()=>{},setImageReset:()=>{},setValues:()=>{},setFiles:()=>{},setVideoInfo:()=>{},setFileErrors:()=>{},setJob:()=>{},setSourceJob:()=>{},setPending:()=>{},setNotice:()=>{},requestAnimationFrame:fn=>frame=fn});
  const record={reviewAtStart:0,checkingAtStart:false,inputAtStart:{values,files},selectionAtStart:'{}',imageAtStart:0,files:{},videoInfo:{},id:'id',focusAtStart:origin};
  vm.runInContext(code,context);context.restore({},record);assert.equal(card.open,true);document.activeElement=scenario==='moved'?other:body;if(scenario==='review')context.reviewEpoch.current++;frame();assert.equal(focused,scenario==='restore'?1:0);assert.equal(scrolled,focused);
 }
});

test('VACE 이력 입력 조회는 종료 신호를 첨부 요청에 전달하고 대기를 해제한다',async()=>{
 const source=readFileSync(new URL('../../gui/VacePage.jsx',import.meta.url),'utf8');
 const code=source.slice(source.indexOf('  async function readJob('),source.indexOf('  function restore(input,record)'));
 let requestSignal,calls=0;const saved={id:'id',request:{prompt:'p',negative_prompt:'',mode:'m',frames:5,steps:2,seed:1,flow_shift:1,guidance_scale:1,reference_strength:1},attachments:['reference']};
 const {untilAborted}=await import('../../gui/managementCommand.js');
 const context=vm.createContext({AbortController,untilAborted,document:{activeElement:null},inputRef:{current:{}},videoSequences:{current:{}},videoControllers:{current:{}},imageSelectionRevision:{current:0},imageChecking:{current:false},reviewEpoch:{current:0},supportedModes:new Set(['m']),template:null,encodeURIComponent,setTimeout,clearTimeout,fetch:(_url,options)=>{requestSignal=options.signal;return ++calls===1?Promise.resolve({ok:true,json:async()=>saved}):new Promise(()=>{});}});
 vm.runInContext(code,context);const controller=new AbortController(),result=context.readJob('id',{signal:controller.signal});await new Promise(resolve=>setImmediate(resolve));assert.equal(calls,2);controller.abort();await assert.rejects(result,error=>error.name==='AbortError');assert.equal(requestSignal.aborted,true);
});
