import {test} from "node:test";
import assert from "node:assert/strict";
import {classifyQueueUpdate} from "../../gui/chatQueueUpdate.mjs";

const pending={request_id:"request01",revision:1,prompt:"수정"};
const row={request_id:"request01",revision:1,prompt:"원본",state:"queued"};
const view=rows=>({id:"session",chat_queue:rows});

test("변경 전 버전은 미확인으로 유지하고 확인된 수정만 반영으로 표시한다",()=>{
  assert.equal(classifyQueueUpdate(view([row]),"session",pending),"waiting");
  assert.equal(classifyQueueUpdate(view([{...row,revision:2,prompt:"수정"}]),"session",pending),"applied");
  assert.equal(classifyQueueUpdate(view([{...row,revision:2,prompt:"다른 수정"}]),"session",pending),"changed");
  assert.equal(classifyQueueUpdate(view([]),"session",{...pending,cancel:true}),"changed");
  assert.equal(classifyQueueUpdate(view([{...row,state:"dispatching"}]),"session",pending),"changed");
});

test("불완전하거나 중복된 응답은 변경 완료로 간주하지 않는다",()=>{
  assert.equal(classifyQueueUpdate(view([row,row]),"session",pending),"invalid");
  assert.equal(classifyQueueUpdate(view([{...row,revision:0}]),"session",pending),"invalid");
  assert.equal(classifyQueueUpdate({id:"other",chat_queue:[]},"session",pending),"invalid");
  assert.equal(classifyQueueUpdate({id:"session"},"session",pending),"invalid");
});
