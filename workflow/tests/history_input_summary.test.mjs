import test from "node:test";
import assert from "node:assert/strict";
import {historyInputSummary} from "../../gui/historyInputSummary.mjs";

test("Wan 2.1 저장 입력의 동작 LoRA 선택을 구분한다",()=>{
  assert.deepEqual(historyInputSummary({action_lora:true,action_variant:"attack_high",action_strength:0.45},"wan21-i2v"),["동작 LoRA Attack Sprite high · 강도 0.45"]);
  assert.deepEqual(historyInputSummary({action_lora:true,action_strength:1},"wan21-t2v"),["동작 LoRA KXSR · 강도 1"]);
  assert.deepEqual(historyInputSummary({action_lora:false},"wan21-i2v"),["동작 LoRA 사용 안 함"]);
  assert.deepEqual(historyInputSummary({action_lora:true,action_variant:"unknown"},"wan21-i2v"),["동작 LoRA 종류 확인 필요"]);
});

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
