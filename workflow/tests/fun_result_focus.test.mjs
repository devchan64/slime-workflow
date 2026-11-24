import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import vm from 'node:vm';

const source=readFileSync(new URL('../../gui/FunControlPage.jsx',import.meta.url),'utf8');
test('Fun Control 결과가 열릴 때 사용자가 옮긴 초점을 유지한다',()=>{
 const effect=source.match(/useEffect\(\(\)=>\{const focus=focusResult\.current;.*?\},\[job\]\);/)?.[0];assert.ok(effect);
 for(const mode of ['same','moved','other-job']){const body={},origin={},other={};let run,focused=0;const context=vm.createContext({useEffect:fn=>run=fn,focusResult:{current:{id:'one',origin}},job:mode==='other-job'?'two':'one',document:{body,activeElement:mode==='moved'?other:origin},resultRef:{current:{focus:()=>focused++,scrollIntoView:()=>{}}}});vm.runInContext(effect,context);run();assert.equal(focused,mode==='same'?1:0);}
});
test('Fun Control 결과 닫기는 일치하는 작업 버튼에만 돌아가고 새 조작을 존중한다',()=>{
 const code=source.slice(source.indexOf('  function closeResult(){'),source.indexOf('  function renderResult('));
 for(const mode of ['lost','moved','new','missing']){const body={},inside={},other={};let frame,focused=0,fallback=0;
  const matching={isConnected:true,matches:()=>false,getAttribute:()=> 'id 작업 결과 보기',focus:()=>focused++},nonmatching={getAttribute:()=> 'other 작업 결과 보기'},summary={isConnected:true,matches:()=>false,focus:()=>fallback++};
  const context=vm.createContext({document:{body,activeElement:inside},job:'id',jobEpoch:{current:1},resultRef:{current:{contains:node=>node===inside}},setJob:()=>context.jobEpoch.current++,resultFocusFrame:{current:null},activeProgressRef:{current:{querySelectorAll:()=>mode==='missing'?[nonmatching]:[nonmatching,matching],querySelector:()=>summary}},requestAnimationFrame:fn=>(frame=fn,1),cancelAnimationFrame:()=>{}});
  vm.runInContext(code+'\nthis.closeResult=closeResult;',context);context.closeResult();context.document.activeElement=mode==='moved'?other:body;if(mode==='new')context.jobEpoch.current++;frame();assert.equal(focused,mode==='lost'?1:0);assert.equal(fallback,mode==='missing'?1:0);
 }
});
