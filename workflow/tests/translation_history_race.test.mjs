import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import vm from 'node:vm';
import {untilAborted} from '../../gui/managementCommand.js';

const source=readFileSync(new URL('../../gui/TranslationPage.jsx',import.meta.url),'utf8');
const functions=source.slice(source.indexOf('  async function readJob('),source.indexOf('  return <section'));
function fixture(){
 const body={},origin={},other={},frames=[];let focused=0;
 const context=vm.createContext({AbortController,DOMException,setTimeout,clearTimeout,untilAborted,service:'prompt-translation',
  document:{body,activeElement:origin},inputRef:{current:{text:'기존',language:'en',terms:''}},inputCard:{current:{open:false}},reviewEpoch:{current:0},reviewRefState:{current:null},restoreFrame:{current:null},
  textRef:{current:{isConnected:true,disabled:false,focus:()=>focused++}},setText:()=>{},setLanguage:()=>{},setTerms:()=>{},setTermsError:()=>{},setNotice:()=>{},
  requestAnimationFrame:fn=>(frames.push(fn),frames.length),cancelAnimationFrame:()=>{},managementCommand:()=>new Promise(()=>{})});
 vm.runInContext(functions+'\nthis.readJob=readJob;this.restore=restore;',context);
 return {context,body,origin,other,frames,focused:()=>focused};
}
const input={text:'복원',target_language:'en',glossary:[]};
test('번역 이력 조회는 상위 중단을 따른다',async()=>{
 const {context}=fixture(),controller=new AbortController();
 const promise=context.readJob('id',{signal:controller.signal});controller.abort();
 await assert.rejects(promise,{name:'AbortError'});
});
test('번역 이력 연속 복원은 먼저 적용한 입력을 보존한다',()=>{
 const {context}=fixture();const record={inputAtStart:context.inputRef.current,reviewAtStart:0,focusAtStart:context.document.activeElement};
 context.restore(input,record);
 assert.equal(context.inputCard.current.open,true);
 assert.throws(()=>context.restore({...input,text:'늦은 입력'},record),/작성 내용이 변경/);
 assert.equal(context.inputRef.current.text,'복원');
});
test('번역 이력 복원 초점은 사용자의 이동과 새 검토를 존중한다',()=>{
 for(const mode of ['unchanged','moved','review']){
  const f=fixture(),{context}=f,record={inputAtStart:context.inputRef.current,reviewAtStart:0,focusAtStart:f.origin};
  context.restore(input,record);
  if(mode==='moved')context.document.activeElement=f.other;
  if(mode==='review')context.reviewEpoch.current++;
  f.frames[0]();assert.equal(f.focused(),mode==='unchanged'?1:0);
 }
});
test('번역 검토는 렌더 전 갱신한 입력을 사용하고 빈 원문에 초점을 둔다',()=>{
 const code=source.slice(source.indexOf('  function review(){'),source.indexOf('  async function submit(){'));
 let pending,notice,focused=0;const document={activeElement:{}};
 const context=vm.createContext({document,reviewEpoch:{current:0},inputRef:{current:{text:'최신',language:'zh-CN',terms:'x'}},reviewOrigin:{current:null},textRef:{current:{focus:()=>focused++}},termsRef:{current:{focus:()=>{}}},parseTranslationGlossary:terms=>[terms],setPending:value=>pending=value,setTermsError:()=>{},setNotice:value=>notice=value});
 vm.runInContext(code+'\nthis.review=review;',context);context.review();
 assert.equal(pending.text,'최신');assert.equal(pending.target_language,'zh-CN');
 context.inputRef.current.text=' ';context.review();assert.match(notice,/원문/);assert.equal(focused,1);
});
test('번역 검토 취소 초점은 새 검토나 사용자의 이동을 방해하지 않는다',()=>{
 const code=source.slice(source.indexOf('  function cancelReview(){'),source.indexOf('  async function submit(){'));
 for(const mode of ['lost','moved','review']){
  const body={},origin={},other={},document={body,activeElement:origin};let frame,focused=0;
  const context=vm.createContext({document,reviewEpoch:{current:1},reviewRef:{current:{contains:element=>element===origin}},restoreFrame:{current:null},textRef:{current:{isConnected:true,disabled:false,focus:()=>focused++}},setPending:()=>{},requestAnimationFrame:fn=>(frame=fn,1),cancelAnimationFrame:()=>{},visibleFocusTarget:target=>target,restoreLostFocus:(doc,target)=>{if(doc.activeElement===doc.body && target.isConnected && !target.disabled)target.focus();}});
  vm.runInContext(code+'\nthis.cancelReview=cancelReview;',context);context.cancelReview();
  document.activeElement=mode==='moved'?other:body;if(mode==='review')context.reviewEpoch.current++;
  frame();assert.equal(focused,mode==='lost'?1:0);
 }
});
test('번역 접수 실패는 이전 작업을 유지하고 이력 확인을 오류로 안내한다',async()=>{
 const code=source.slice(source.indexOf('  async function submit(){'),source.indexOf('  async function readJob('));
 let notice,options,selected='기존',busy=false;
 const context=vm.createContext({AbortController,setTimeout,clearTimeout,untilAborted,service:'prompt-translation',submitRequest:{current:null},pending:{text:'원문'},sending:{current:false},model:{},generationReady:()=>true,setBusy:value=>busy=value,managementCommand:async()=>{throw new Error('연결 실패');},requestErrorMessage:error=>error.message,setNotice:(message,settings)=>{notice=message;options=settings;},setRecord:()=>{},setJob:value=>selected=value,setPending:()=>{},job:'기존'});
 vm.runInContext(code+'\nthis.submit=submit;',context);await context.submit();
 assert.equal(selected,'기존');assert.match(notice,/이력을 조회해 접수 여부/);assert.match(notice,/이전에 선택/);assert.equal(options.error,true);assert.equal(busy,false);
});
test('번역 접수 지연은 시간 초과 후 이력 확인을 안내하고 중복 요청을 막는다',async()=>{
 const code=source.slice(source.indexOf('  async function submit(){'),source.indexOf('  async function readJob('));
 let timeout,notice,busy=false,calls=0;
 const context=vm.createContext({AbortController,untilAborted,service:'prompt-translation',setTimeout:fn=>(timeout=fn,1),clearTimeout:()=>{},submitRequest:{current:null},pending:{text:'원문'},sending:{current:false},model:{},generationReady:()=>true,setBusy:value=>busy=value,managementCommand:()=>{calls++;return new Promise(()=>{});},requestErrorMessage:error=>error.message,setNotice:message=>notice=message,setRecord:()=>{},setJob:()=>{},setPending:()=>{},job:''});
 vm.runInContext(code+'\nthis.submit=submit;',context);const first=context.submit();await context.submit();assert.equal(calls,1);timeout();await first;
 assert.match(notice,/시간이 초과/);assert.match(notice,/이력을 조회해 접수 여부/);assert.equal(busy,false);assert.equal(context.sending.current,false);
});
