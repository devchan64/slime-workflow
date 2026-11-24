import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import vm from 'node:vm';
import {restoreLostFocus} from '../../gui/restoreLostFocus.mjs';

const source=readFileSync(new URL('../../gui/BillboardCatalog.jsx',import.meta.url),'utf8');
test('빌보드 상세 닫기는 잃은 초점만 복구하고 새 선택의 초점을 빼앗지 않는다',()=>{
  const start=source.indexOf('  function closeDetail(){'),end=source.indexOf('\n  const resultsStale=',start);assert.ok(start>=0 && end>start);
  for(const state of ['body','other','new','missing']){
    const body={},document={body,activeElement:state==='other'?{}:body};let scheduled,focused='',selected=true;
    const trigger={isConnected:state!=='missing',focus(){focused='trigger';}},search={isConnected:true,focus(){focused='search';}};
    const context=vm.createContext({document,focusEpoch:{current:0},triggerRef:{current:trigger},searchRef:{current:search},select:value=>selected=value,requestAnimationFrame:fn=>scheduled=fn,restoreLostFocus});
    vm.runInContext(source.slice(start,end)+'\nthis.closeDetail=closeDetail;',context);context.closeDetail();if(state==='new')context.focusEpoch.current++;scheduled();
    assert.equal(selected,null);assert.equal(focused,state==='body'?'trigger':state==='missing'?'search':'');
  }
});
test('빌보드 상세를 열 때 이미 이동한 초점은 유지한다',()=>{
  const start=source.indexOf('  useEffect(()=>{if(selected && triggerRef.current'),end=source.indexOf('\n',start);assert.ok(start>=0 && end>start);
  for(const state of ['trigger','body','other']){
    const body={},trigger={},document={body,activeElement:state==='body'?body:state==='trigger'?trigger:{}};let focused=false;
    const context=vm.createContext({document,selected:{id:'x'},triggerRef:{current:trigger},detailRef:{current:{focus(){focused=true;}}},useEffect:fn=>fn()});
    vm.runInContext(source.slice(start,end),context);assert.equal(focused,state!=='other');
  }
});
