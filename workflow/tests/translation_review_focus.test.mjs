import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import vm from 'node:vm';
import {restoreLostFocus,visibleFocusTarget} from '../../gui/restoreLostFocus.mjs';

test('번역 검토가 열릴 때 사용자가 옮긴 초점은 유지한다',()=>{
 const source=readFileSync(new URL('../../gui/TranslationPage.jsx',import.meta.url),'utf8');
 const effect=source.match(/useEffect\(\(\)=>\{if\(!pending\)return;const origin=reviewOrigin\.current;.*?\},\[pending\]\);/s)?.[0];assert.ok(effect);
 for(const moved of [false,true]){
  let run,frame,focused=0,cancelled=0;const body={},origin={},other={},document={body,activeElement:origin};
  const context=vm.createContext({pending:{},document,reviewOrigin:{current:origin},reviewRef:{current:{isConnected:true,focus:()=>focused++}},useEffect:fn=>run=fn,requestAnimationFrame:fn=>(frame=fn,1),cancelAnimationFrame:()=>cancelled++});
  vm.runInContext(effect,context);const cleanup=run();document.activeElement=moved?other:body;frame();cleanup();assert.equal(focused,moved?0:1);assert.equal(cancelled,1);
 }
});

test('번역 검토를 취소할 때 접힌 입력 카드의 제목으로 초점을 복구한다',()=>{
 const source=readFileSync(new URL('../../gui/TranslationPage.jsx',import.meta.url),'utf8');
 const start=source.indexOf('  function cancelReview()'),end=source.indexOf('  async function submit()',start);
 let frame,focused='';const body={},button={},document={body,activeElement:button};
 const summary={isConnected:true,focus:()=>focused='summary'};
 const target={isConnected:true,focus:()=>focused='input',parentElement:{tagName:'DETAILS',open:false,querySelector:()=>summary}};
 const context=vm.createContext({document,restoreLostFocus,visibleFocusTarget,reviewRef:{current:{contains:node=>node===button}},reviewEpoch:{current:0},restoreFrame:{current:null},textRef:{current:target},setPending:()=>{},requestAnimationFrame:fn=>(frame=fn,1),cancelAnimationFrame:()=>{}});
 vm.runInContext(source.slice(start,end),context);context.cancelReview();document.activeElement=body;frame();assert.equal(focused,'summary');
});
