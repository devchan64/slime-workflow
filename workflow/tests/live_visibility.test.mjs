import test from "node:test";
import assert from "node:assert/strict";
import {observeLiveVisibility} from "../../gui/observeLiveVisibility.mjs";

test("관찰 기능이 없으면 화면 위치와 탭 상태를 추적하고 종료 후 해제한다",()=>{
  const doc=new EventTarget(),view=new EventTarget(),observed=[];
  doc.visibilityState="visible";view.innerWidth=360;view.innerHeight=640;
  let top=20;
  const element={getBoundingClientRect:()=>({top,bottom:top+20,left:0,right:20})};
  const stop=observeLiveVisibility(element,value=>observed.push(value),{document:doc,window:view});
  assert.equal(observed.at(-1),true);
  top=700;view.dispatchEvent(new Event("scroll"));assert.equal(observed.at(-1),false);
  top=10;view.dispatchEvent(new Event("resize"));assert.equal(observed.at(-1),true);
  doc.visibilityState="hidden";doc.dispatchEvent(new Event("visibilitychange"));assert.equal(observed.at(-1),false);
  stop();const count=observed.length;view.dispatchEvent(new Event("scroll"));doc.dispatchEvent(new Event("visibilitychange"));assert.equal(observed.length,count);
});

test("대체 판정은 중첩 스크롤 영역에 가려진 항목을 갱신하지 않는다",()=>{
  const doc=new EventTarget(),view=new EventTarget(),observed=[];
  doc.visibilityState="visible";view.innerWidth=360;view.innerHeight=640;
  view.getComputedStyle=node=>node.style;
  const parent={style:{overflowX:"visible",overflowY:"auto"},getBoundingClientRect:()=>({left:0,right:360,top:100,bottom:200})};
  let top=250;
  const element={parentElement:parent,getBoundingClientRect:()=>({left:0,right:20,top,bottom:top+20})};
  const stop=observeLiveVisibility(element,value=>observed.push(value),{document:doc,window:view});
  assert.equal(observed.at(-1),false);
  top=190;view.dispatchEvent(new Event("scroll"));assert.equal(observed.at(-1),true);
  top=200;view.dispatchEvent(new Event("scroll"));assert.equal(observed.at(-1),false);
  stop();
});
