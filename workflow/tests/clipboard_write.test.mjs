import {test} from "node:test";
import assert from "node:assert/strict";
import {writeClipboardText} from "../../gui/clipboardWrite.mjs";

test("응답하지 않는 복사는 시간 초과되고 늦은 완료를 성공으로 바꾸지 않는다",async()=>{
  let finish;
  Object.defineProperty(globalThis,"navigator",{configurable:true,value:{clipboard:{writeText:()=>new Promise(resolve=>{finish=resolve;})}}});
  try {
    const result=writeClipboardText("내용",10);
    await assert.rejects(result,/시간 초과/);
    finish();
  } finally {delete globalThis.navigator;}
});
