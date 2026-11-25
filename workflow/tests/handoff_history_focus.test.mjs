import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import vm from 'node:vm';

test('양도 이력 페이지 크기를 바꿀 때 사라진 초점만 복구한다',()=>{
 const source=readFileSync(new URL('../../gui/GpuHandoffHistory.jsx',import.meta.url),'utf8');
 const start=source.indexOf('  function changeSize(value){'),end=source.indexOf('\n  return <section',start);
 assert.ok(start>=0 && end>start);
 for(const moved of [false,true]){
  const origin={},other={},body={},document={activeElement:origin,body};let frame,focused=0,size,page;
  const context=vm.createContext({document,setSize:v=>size=v,setPage:v=>page=v,requestAnimationFrame:fn=>frame=fn,refreshButton:{current:{focus:()=>focused++}}});
  vm.runInContext(source.slice(start,end),context);context.changeSize(10);document.activeElement=moved?other:body;frame();
  assert.equal(size,10);assert.equal(page,0);assert.equal(focused,moved?0:1);
 }
});
