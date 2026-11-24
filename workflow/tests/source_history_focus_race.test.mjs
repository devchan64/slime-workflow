import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import vm from 'node:vm';
import {untilAborted} from '../../gui/managementCommand.js';

const source=readFileSync(new URL('../../gui/SourceHistory.jsx',import.meta.url),'utf8');
test('대화 이력 결과 닫기는 새 선택과 사용자가 옮긴 초점을 존중한다',()=>{
 const code=source.slice(source.indexOf('  function closeResult(){'),source.indexOf('  function openResult('));
 for(const mode of ['lost','moved','new']){
  const body={},inside={},other={};let frame,focused=0;
  const context=vm.createContext({document:{body,activeElement:inside},resultRef:{current:{contains:node=>node===inside}},resultTrigger:{current:{isConnected:true,matches:()=>false,focus:()=>focused++}},selectionEpoch:{current:1},resultFocusFrame:{current:null},selectJob:()=>context.selectionEpoch.current++,requestAnimationFrame:fn=>(frame=fn,1),cancelAnimationFrame:()=>{}});
  vm.runInContext(code+'\nthis.closeResult=closeResult;',context);context.closeResult();context.document.activeElement=mode==='moved'?other:body;if(mode==='new')context.selectionEpoch.current++;frame();assert.equal(focused,mode==='lost'?1:0);
 }
});
test('이력 목록이 바뀌어 이전 버튼이 없으면 결과 닫기 후 검색란으로 돌아간다',()=>{
 const code=source.slice(source.indexOf('  function closeResult(){'),source.indexOf('  function openResult('));
 const body={},inside={};let frame,focused=0;
 const context=vm.createContext({document:{body,activeElement:inside},resultRef:{current:{contains:node=>node===inside}},resultTrigger:{current:{isConnected:false}},searchRef:{current:{isConnected:true,matches:()=>false,focus:()=>focused++}},selectionEpoch:{current:1},resultFocusFrame:{current:null},selectJob:()=>context.selectionEpoch.current++,requestAnimationFrame:fn=>(frame=fn,1),cancelAnimationFrame:()=>{}});
 vm.runInContext(code+'\nthis.closeResult=closeResult;',context);context.closeResult();context.document.activeElement=body;frame();assert.equal(focused,1);
});
test('대화 이력 조회 중 새 결과 선택은 늦은 목록 응답이 지우지 않는다',async()=>{
 const code=source.slice(source.indexOf('  async function load('),source.indexOf('  function cleaned('));let resolve,selected='새 작업',page,selectionChanges=0;
 const context=vm.createContext({AbortController,untilAborted,setTimeout,clearTimeout,query:'',selectionEpoch:{current:0},request:{current:{start:()=>1,isCurrent:()=>true}},controllerRef:{current:null},source:{service:'writer-agent',command:'history'},managementCommand:()=>new Promise(done=>resolve=done),validSourceHistoryPage:()=>true,focusList:{current:false},setBusy:()=>{},setError:()=>{},setPage:value=>page=value,setReceivedAt:()=>{},setFilter:()=>{},selectJob:value=>{selected=value;selectionChanges++;},failedPageTrigger:{current:null}});
 vm.runInContext(code+'\nthis.load=load;',context);const pending=context.load(0,undefined,true);context.selectionEpoch.current++;resolve({records:[]});await pending;
 assert.equal(selected,'새 작업');assert.equal(selectionChanges,0);assert.equal(context.focusList.current,false);assert.ok(page);
});
test('대화 이력 검색 성공은 열려 있는 결과를 유지한다',async()=>{
 const code=source.slice(source.indexOf('  async function load('),source.indexOf('  function cleaned('));let selected='열린 작업',page;
 const context=vm.createContext({AbortController,untilAborted,setTimeout,clearTimeout,query:'',selectionEpoch:{current:0},request:{current:{start:()=>1,isCurrent:()=>true}},controllerRef:{current:null},source:{service:'writer-agent',command:'history'},managementCommand:async()=>({records:[]}),validSourceHistoryPage:()=>true,focusList:{current:false},setBusy:()=>{},setError:()=>{},setPage:value=>page=value,setReceivedAt:()=>{},setFilter:()=>{},selectJob:value=>selected=value,failedPageTrigger:{current:null}});
 vm.runInContext(code+'\nthis.load=load;',context);await context.load(0,undefined,true);assert.equal(selected,'열린 작업');assert.ok(page);
});
