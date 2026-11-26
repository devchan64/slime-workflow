import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import vm from 'node:vm';
import {restoreLostFocus} from '../../gui/restoreLostFocus.mjs';

test('오디오 검토는 사용자가 조회 중 옮긴 초점을 유지하고 종료 시 예약을 취소한다',()=>{
 const source=readFileSync(new URL('../../gui/SoundEffectPage.jsx',import.meta.url),'utf8');
 const effect=source.match(/useEffect\(\(\)=>\{if\(!review\)return;const origin=reviewOrigin\.current;.*?\},\[review\]\);/s)?.[0];
 assert.ok(effect);
 for(const scenario of ['origin','lost','moved']){
  let run,frame,focused=0,cancelled=0;const body={},origin={},other={},document={body,activeElement:origin};
  const context=vm.createContext({document,review:{},reviewOrigin:{current:origin},reviewRef:{current:{isConnected:true,focus:()=>focused++}},useEffect:fn=>run=fn,requestAnimationFrame:fn=>(frame=fn,1),cancelAnimationFrame:()=>cancelled++});
  vm.runInContext(effect,context);const cleanup=run();document.activeElement=scenario==='origin'?origin:scenario==='lost'?body:other;frame();cleanup();
  assert.equal(focused,scenario==='moved'?0:1);assert.equal(cancelled,1);
 }
});

test('오디오 검토 실패는 사라진 초점만 실행 위치로 복구한다',()=>{
 const source=readFileSync(new URL('../../gui/SoundEffectPage.jsx',import.meta.url),'utf8');
 const effect=source.match(/useEffect\(\(\)=>\{if\(busy \|\| !noticeError \|\| !reviewOrigin\.current\).*?\},\[busy,noticeError,notice\]\);/s)?.[0];
 assert.ok(effect);
 for(const moved of [false,true]){
  let run,frame,focused=0;const body={},origin={isConnected:true,focus:()=>focused++},document={body,activeElement:moved?{}:body},reviewOrigin={current:origin};
  const context=vm.createContext({busy:false,noticeError:true,notice:'오류',reviewOrigin,document,restoreLostFocus,visibleFocusTarget:value=>value,useEffect:fn=>run=fn,requestAnimationFrame:fn=>(frame=fn,1),cancelAnimationFrame:()=>{}});
  vm.runInContext(effect,context);run();frame();assert.equal(focused,moved?0:1);assert.equal(reviewOrigin.current,null);
 }
});
