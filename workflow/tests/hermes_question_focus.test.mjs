import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import vm from 'node:vm';
import {restoreLostFocus,visibleFocusTarget} from '../../gui/restoreLostFocus.mjs';

test('질문 대상 재확인은 잃은 초점만 결과에 복구한다',()=>{
 const source=readFileSync(new URL('../../gui/HermesQuestionForm.jsx',import.meta.url),'utf8');
 const effect=source.match(/useEffect\(\(\)=>\{\s*if\(targetState\.status==='loading' \|\| !restoreRetryFocus\.current\)return;[\s\S]*?\},\[targetState\]\);/)?.[0];assert.ok(effect);
 for(const status of ['ready','error'])for(const moved of [false,true]){
  let frame,focused='';const body={},document={body,activeElement:moved?{}:body};
  const retry={isConnected:true,focus:()=>focused='retry'},target={isConnected:true,focus:()=>focused='target'};
  const context=vm.createContext({useEffect:fn=>fn(),targetState:{status},restoreRetryFocus:{current:true},retryRef:{current:retry},targetRef:{current:target},document,requestAnimationFrame:fn=>(frame=fn,1),cancelAnimationFrame:()=>{},restoreLostFocus,visibleFocusTarget});
  vm.runInContext(effect,context);frame();assert.equal(focused,moved?'':status==='ready'?'target':'retry');
 }
});
