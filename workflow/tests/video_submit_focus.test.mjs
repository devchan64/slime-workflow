import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import vm from 'node:vm';
import {restoreLostFocus,visibleFocusTarget} from '../../gui/restoreLostFocus.mjs';

test('영상 접수 종료 후 접힌 입력 카드의 보이는 제목으로 잃은 초점만 복구한다',()=>{
 for(const file of ['I2VPage.jsx','MiniMaxH3Page.jsx','MiniMaxH3Ref2VAPage.jsx']){
  const source=readFileSync(new URL('../../gui/'+file,import.meta.url),'utf8');
  const submit=source.slice(source.indexOf('  async function submit()'),source.indexOf('\n  }',source.indexOf('  async function submit()')));
  const expression=submit.match(/if\(restore\)requestAnimationFrame\(\(\)=>restoreLostFocus\(document,visibleFocusTarget\(formRef\.current\)\)\)/)?.[0];assert.ok(expression,file);
  for(const moved of [false,true]){
   let frame,focused=0;const body={},other={},document={body,activeElement:moved?other:body},summary={isConnected:true,focus:()=>focused++},details={tagName:'DETAILS',open:false,parentElement:null,querySelector:()=>summary};
   const context=vm.createContext({document,restore:true,restoreLostFocus,visibleFocusTarget,formRef:{current:{parentElement:details}},requestAnimationFrame:fn=>frame=fn});vm.runInContext(expression,context);frame();assert.equal(focused,moved?0:1,file);
  }
 }
});
