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

test("pose options distinguish excluded values from unavailable settings",()=>{
  assert.deepEqual(historyInputSummary({pose_include_hands:true,pose_include_face:false}),["손 상세 포함","얼굴 상세 제외"]);
  assert.deepEqual(historyInputSummary({pose_include_hands:"false"}),[]);
});

test("DWPose omits fixed generation parameters while other generators retain them",()=>{
  const request={width:832,height:480,frames:1,steps:1,seed:0,pose_include_hands:true};
  assert.deepEqual(historyInputSummary(request,"dwpose"),["832 × 480","손 상세 포함"]);
  assert.deepEqual(historyInputSummary(request,"wan22-fun-control"),["832 × 480","1프레임","1스텝","시드 0","손 상세 포함"]);
});
