import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import vm from 'node:vm';
import {restoreLostFocus} from '../../gui/restoreLostFocus.mjs';

test('키프레임 미리보기 닫기는 미리보기에서 사라진 초점만 복구한다',()=>{
 const source=readFileSync(new URL('../../gui/KeyframeCatalog.jsx',import.meta.url),'utf8');
 const code=source.slice(source.indexOf('  function closePreview()'),source.indexOf('  function changePage('));
 for(const scenario of ['lost','moved','outside']){
  let frame,focused=0;const body={},inside={},other={},document={body,activeElement:scenario==='outside'?other:inside};
  const context=vm.createContext({document,restoreLostFocus,previewRef:{current:{contains:value=>value===inside}},triggerRef:{current:{isConnected:true,focus:()=>focused++}},previewFocusFrame:{current:null},select:()=>{},requestAnimationFrame:fn=>(frame=fn,1),cancelAnimationFrame:()=>{}});
  vm.runInContext(code,context);context.closePreview();document.activeElement=scenario==='lost'?body:other;frame?.();
  assert.equal(focused,scenario==='lost'?1:0,scenario);
 }
});
