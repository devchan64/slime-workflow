import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import vm from 'node:vm';

const html=readFileSync(new URL('../../gui/ui/asset_review/walk-sheet.html',import.meta.url),'utf8');
const loadScript=html.split('\n').find(value=>value.startsWith('Promise.all(reviewAssetRecords'));
const controlsScript=html.split('\n').find(value=>value.startsWith('const reviewControls='));

async function run(mode,restoreRetryFocus=false,focusMoved=false){
  const images=[],timers=[],cleared=[],status={textContent:'loading'},error={textContent:''},retry={hidden:true},controls=[{disabled:false},{disabled:false}];
  let renders=0,playback=0,focused='';const body={};retry.focus=()=>focused='retry';
  class Image {constructor(){images.push(this);} set src(value){this.filename=value;}}
  const context=vm.createContext({reviewAssetRecords:[{image:'walk.png',direction:'down_left'}],Image,
    setTimeout:callback=>{timers.push(callback);return timers.length-1;},clearTimeout:id=>cleared.push(id),
    loadedSheetImages:{},pendingImageCleanups:[],reviewLoadStatus:status,retryReviewButton:retry,reviewImagesReady:false,
    restoreRetryFocus,directionButtonElements:[{focus:()=>focused='direction'}],document:{body,activeElement:focusMoved?{}:body,querySelector:()=>error,querySelectorAll:()=>controls},renderReviewPanels:()=>renders++,requestAnimationFrame:()=>playback++,updatePlaybackClock:()=>{}});
  vm.runInContext(controlsScript,context);
  assert.ok(controls.every(control=>control.disabled));
  vm.runInContext(loadScript,context);
  if(mode==='success')images.forEach(image=>image.onload());
  else if(mode==='failure')images[0].onerror();
  else timers[0]();
  await new Promise(resolve=>setImmediate(resolve));
  return {status,error,retry,renders,playback,cleared,controls,images,focused,ready:context.reviewImagesReady};
}

test('걷기 비교 이미지 로딩 성공·실패·시간 초과를 구분한다',async()=>{
  const success=await run('success');
  assert.equal(success.status.textContent,'');assert.equal(success.error.textContent,'');assert.equal(success.retry.hidden,true);
  assert.equal(success.renders,1);assert.equal(success.playback,1);assert.equal(success.cleared.length,2);
  assert.equal(success.ready,true);assert.ok(success.controls.every(control=>!control.disabled));
  for(const [mode,message] of [['failure','로드 실패'],['timeout','시간 초과']]){
    const result=await run(mode);
    assert.match(result.error.textContent,new RegExp(message));assert.equal(result.status.textContent,'');
    assert.equal(result.retry.hidden,false);assert.equal(result.renders,0);assert.equal(result.playback,0);
    assert.equal(result.ready,false);assert.ok(result.controls.every(control=>control.disabled));
    assert.equal(result.cleared.length,2);assert.ok(result.images.every(image=>image.onload===null && image.onerror===null));
  }
});

test('재시도 뒤 사용자가 초점을 옮기지 않았다면 결과에 맞게 복구한다',async()=>{
  assert.equal((await run('success',true)).focused,'direction');
  assert.equal((await run('failure',true)).focused,'retry');
  assert.equal((await run('success',true,true)).focused,'');
  assert.equal((await run('failure',true,true)).focused,'');
});
