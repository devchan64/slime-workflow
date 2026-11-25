import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import vm from 'node:vm';

test('배치 삭제 후 남은 배치 또는 검색 영역으로 초점을 복구한다',()=>{
 const source=readFileSync(new URL('../../gui/KeyframeCatalog.jsx',import.meta.url),'utf8');
 const effect=source.split('\n').find(line=>line.includes('useEffect(()=>{if(focusRemoval.current)'));
 for(const [count,where,expected] of [[1,'body','placement'],[0,'body','search'],[1,'origin','placement'],[1,'other',null]]){
  const origin={},body={},other={};let focused=null;
  const context=vm.createContext({rows:Array(count),focusRemoval:{current:origin},document:{body,activeElement:{body,origin,other}[where]},
   placementRef:{current:{focus:()=>focused='placement'}},searchRef:{current:{focus:()=>focused='search'}},useEffect:fn=>fn()});
  vm.runInContext(effect,context);
  assert.equal(focused,expected);assert.equal(context.focusRemoval.current,null);
 }
});

test('키프레임 추가 후 사용자가 옮긴 초점은 유지한다',()=>{
 const source=readFileSync(new URL('../../gui/KeyframeCatalog.jsx',import.meta.url),'utf8');
 const effect=source.split('\n').find(line=>line.includes('useEffect(()=>{if(rows.length && focusPlacement.current)'));
 assert.ok(effect);
 for(const where of ['body','origin','other']){
  const origin={},body={},other={};let focused=0,scrolled=0;
  const context=vm.createContext({rows:[{}],focusPlacement:{current:origin},document:{body,activeElement:{body,origin,other}[where]},
   placementRef:{current:{focus:()=>focused++,scrollIntoView:()=>scrolled++}},useEffect:fn=>fn()});
  vm.runInContext(effect,context);
  assert.equal(focused,where==='other'?0:1);assert.equal(scrolled,focused);assert.equal(context.focusPlacement.current,null);
 }
});
