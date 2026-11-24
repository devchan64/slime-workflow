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
