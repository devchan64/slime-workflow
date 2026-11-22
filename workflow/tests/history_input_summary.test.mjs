import test from "node:test";
import assert from "node:assert/strict";
import {historyInputSummary} from "../../gui/historyInputSummary.mjs";

test("summarizes supported saved fields without inventing missing values",()=>{
  assert.deepEqual(historyInputSummary({tag:" test ",width:832,height:480,frames:21,steps:20,seed:0,prompt:"private"}),["태그 test","832 × 480","21프레임","20스텝","시드 0"]);
  assert.deepEqual(historyInputSummary({width:832,frames:-1,seed:"42"}),[]);
  assert.deepEqual(historyInputSummary(null),[]);
});

 test("audio summary shows only verified output and finite duration",()=>{
  assert.deepEqual(historyInputSummary({duration_seconds:12.5,audio_available:true}),["길이 12.5초","WAV 오디오 결과"]);
  assert.deepEqual(historyInputSummary({duration_seconds:Infinity,audio_available:false}),[]);
});
