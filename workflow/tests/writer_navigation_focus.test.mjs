import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import vm from 'node:vm';

const source=readFileSync(new URL('../../gui/WriterPage.jsx',import.meta.url),'utf8');
test('작가 결과를 열 때 사용자가 옮긴 초점은 유지한다',()=>{
 const effect=source.match(/useEffect\(\(\)=>\{if\(selected && resultTrigger\.current.*?\},\[selected\]\);/s)?.[0];assert.ok(effect);
 for(const moved of [false,true]){const body={},trigger={},other={};let run,focused=0;
  const context=vm.createContext({selected:'id',resultTrigger:{current:trigger},document:{body,activeElement:moved?other:trigger},focusResult:()=>focused++,useEffect:fn=>run=fn});vm.runInContext(effect,context);run();assert.equal(focused,moved?0:1);
 }
});
test('작가 결과 닫기 후 새 선택이나 사용자 이동을 방해하지 않는다',()=>{
 const code=source.slice(source.indexOf('  function closeResult(){'),source.indexOf('  async function search(){'));
 for(const mode of ['lost','moved','new']){const body={},inside={},other={};let frame,focused=0;
  const context=vm.createContext({document:{body,activeElement:inside},resultTrigger:{current:{isConnected:true,matches:()=>false,focus:()=>focused++}},resultRef:{current:{contains:node=>node===inside}},selectionEpoch:{current:1},select:()=>context.selectionEpoch.current++,resultFocusFrame:{current:null},requestAnimationFrame:fn=>(frame=fn,1),cancelAnimationFrame:()=>{}});
  vm.runInContext(code+'\nthis.closeResult=closeResult;',context);context.closeResult();context.document.activeElement=mode==='moved'?other:body;if(mode==='new')context.selectionEpoch.current++;frame();assert.equal(focused,mode==='lost'?1:0);
 }
});
test('작가 목록 갱신으로 원래 버튼이 사라지면 결과 닫기 후 검색으로 돌아간다',()=>{
 const code=source.slice(source.indexOf('  function closeResult(){'),source.indexOf('  async function search(){'));
 const body={},inside={};let frame,focused=0;
 const context=vm.createContext({document:{body,activeElement:inside},resultRef:{current:{contains:node=>node===inside}},resultTrigger:{current:{isConnected:false}},searchButton:{current:{isConnected:true,matches:()=>false,focus:()=>focused++}},selectionEpoch:{current:1},resultFocusFrame:{current:null},select:()=>context.selectionEpoch.current++,requestAnimationFrame:fn=>(frame=fn,1),cancelAnimationFrame:()=>{}});
 vm.runInContext(code+'\nthis.closeResult=closeResult;',context);context.closeResult();context.document.activeElement=body;frame();assert.equal(focused,1);
});
