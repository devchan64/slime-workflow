import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import vm from 'node:vm';

test('번역 검토가 열릴 때 사용자가 옮긴 초점은 유지한다',()=>{
 const source=readFileSync(new URL('../../gui/TranslationPage.jsx',import.meta.url),'utf8');
 const effect=source.match(/useEffect\(\(\)=>\{if\(!pending\)return;const origin=reviewOrigin\.current;.*?\},\[pending\]\);/s)?.[0];assert.ok(effect);
 for(const moved of [false,true]){
  let run,frame,focused=0,cancelled=0;const body={},origin={},other={},document={body,activeElement:origin};
  const context=vm.createContext({pending:{},document,reviewOrigin:{current:origin},reviewRef:{current:{isConnected:true,focus:()=>focused++}},useEffect:fn=>run=fn,requestAnimationFrame:fn=>(frame=fn,1),cancelAnimationFrame:()=>cancelled++});
  vm.runInContext(effect,context);const cleanup=run();document.activeElement=moved?other:body;frame();cleanup();assert.equal(focused,moved?0:1);assert.equal(cancelled,1);
 }
});
