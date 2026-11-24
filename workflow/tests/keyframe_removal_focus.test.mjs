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
