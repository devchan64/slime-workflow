import {test} from "node:test";
import assert from "node:assert/strict";
import {drawAlignment} from "../../gui/drawAlignment.js";

test("정렬 재생은 실제로 표시한 프레임을 캔버스에 기록한다",async()=>{
  const originalImage=globalThis.Image,originalRaf=globalThis.requestAnimationFrame;
  let nextFrame;
  globalThis.Image=class {width=400;height=200;set src(value){queueMicrotask(()=>this.onload());}};
  globalThis.requestAnimationFrame=callback=>{nextFrame=callback;return 1;};
  const ctx={clearRect(){},fillRect(){},drawImage(){},strokeRect(){},fillText(){}};
  const canvas={isConnected:true,getContext:()=>ctx};
  const renderer=`data:text/javascript,${encodeURIComponent("export const calculateEffectFramePlacement=()=>({left:0,top:0,width:1,height:1});export const sampleEffectAnimationFrame=()=>3;export const sampleMothAnimationFrame=()=>null;export const sampleFogAnimationFrame=()=>null;")}`;
  const detail={rendererModule:renderer,sheetImage:"sheet",document:{renderer:"effect",alignment:{texture:"effect"}}};
  const values={target:[0,0,1,1],frames:Array.from({length:8},()=>[0,0,1,1]),alpha:1};
  try{
    await drawAlignment(canvas,detail,values,true,0,false,false);
    nextFrame(performance.now());
    assert.equal(canvas.effectDisplayedFrame,3);
    canvas.effectPreviewRevision++;
  }finally{globalThis.Image=originalImage;globalThis.requestAnimationFrame=originalRaf;}
});
