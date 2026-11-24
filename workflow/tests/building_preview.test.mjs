import {test} from "node:test";
import assert from "node:assert/strict";
import {drawBuildingPreview} from "../../gui/drawBuildingPreview.js";

test("미리보기 오류와 재시도는 이전 이미지를 지우고 상태를 알린다",()=>{
  const previous=globalThis.Image,images=[];
  globalThis.Image=class {constructor(){images.push(this);}};
  const calls=[],ctx={clearRect:()=>calls.push("clear"),fillRect:()=>{},drawImage:()=>calls.push("draw")};
  const canvas={width:480,height:360,getContext:()=>ctx},status=[];
  try {
    const cleanup=drawBuildingPreview(canvas,"first",null,{},value=>status.push(value));
    assert.deepEqual(status,["loading"]);
    images[0].onerror();
    assert.equal(status.at(-1),"image-error");
    cleanup();
    assert.equal(images[0].onerror,null);
    drawBuildingPreview(canvas,"second",null,{},value=>status.push(value));
    images[1].width=100;images[1].height=100;images[1].onload();
    assert.equal(status.at(-1),"ready");
    assert.equal(calls.filter(call=>call==="clear").length,3);
    assert.equal(calls.at(-1),"draw");
  } finally {globalThis.Image=previous;}
});

test("이미지가 응답하지 않으면 시간 초과를 표시하고 정리 뒤에는 갱신하지 않는다",()=>{
  const originalImage=globalThis.Image,originalSetTimeout=globalThis.setTimeout,originalClearTimeout=globalThis.clearTimeout;
  const timers=[];globalThis.Image=class {};
  globalThis.setTimeout=(callback,delay)=>{const timer={callback,delay,cleared:false};timers.push(timer);return timer;};
  globalThis.clearTimeout=timer=>{timer.cleared=true;};
  const canvas={width:480,height:360,getContext:()=>({clearRect(){}})},status=[];
  try{
    const cleanup=drawBuildingPreview(canvas,'slow',null,{},value=>status.push(value));
    assert.equal(timers[0].delay,15000);timers[0].callback();
    assert.deepEqual(status,['loading','image-error']);cleanup();
    const stop=drawBuildingPreview(canvas,'cancelled',null,{},value=>status.push(value));
    stop();assert.equal(timers[1].cleared,true);timers[1].callback();
    assert.deepEqual(status,['loading','image-error','loading']);
  }finally{globalThis.Image=originalImage;globalThis.setTimeout=originalSetTimeout;globalThis.clearTimeout=originalClearTimeout;}
});
