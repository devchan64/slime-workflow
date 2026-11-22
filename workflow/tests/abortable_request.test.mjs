import {test} from "node:test";
import assert from "node:assert/strict";
import {untilAborted} from "../../gui/managementCommand.js";

test("중단 신호를 무시하는 요청도 대기에서 벗어난다",async()=>{
  const controller=new AbortController();
  const result=untilAborted(new Promise(()=>{}),controller.signal);
  controller.abort();
  await assert.rejects(result,{name:"AbortError"});
});

test("정상 응답은 그대로 반환하고 이미 중단된 요청은 거부한다",async()=>{
  const controller=new AbortController();
  assert.equal(await untilAborted(Promise.resolve("ok"),controller.signal),"ok");
  controller.abort();
  await assert.rejects(untilAborted(Promise.resolve("late"),controller.signal),{name:"AbortError"});
});
