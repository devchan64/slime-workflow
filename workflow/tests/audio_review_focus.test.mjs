import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import vm from 'node:vm';

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
