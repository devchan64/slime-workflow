import {test} from "node:test";
import assert from "node:assert/strict";
import {validMediaResultDetails} from "../../gui/mediaResultValidation.mjs";

test("재생 가능한 오디오 경로나 트랙이 있는 결과만 허용한다",()=>{
  const available={result_status:"available"};
  assert.equal(validMediaResultDetails({...available,audio:"/result.wav",tracks:[]},"audio"),true);
  assert.equal(validMediaResultDetails({...available,tracks:[{label:"원본",wav:"/result.wav"}]},"audio"),true);
  assert.equal(validMediaResultDetails({...available,tracks:[]},"audio"),false);
  assert.equal(validMediaResultDetails({...available,tracks:[{label:"원본",wav:""}]},"audio"),false);
  assert.equal(validMediaResultDetails({...available,tracks:{}},"audio"),false);
  assert.equal(validMediaResultDetails({...available,file_observation:"unavailable"},"audio"),true);
});

test("결과 안내는 문자열이어야 한다",()=>{
  assert.equal(validMediaResultDetails({note:{unexpected:true}},"video"),false);
  assert.equal(validMediaResultDetails({note:"확인됨"},"video"),true);
});

test("완료된 영상과 이미지의 표시 경로가 필요하다",()=>{
  const available={result_status:"available"};
  assert.equal(validMediaResultDetails({...available,video:"/preview.mp4"},"video","wan22-vace"),true);
  assert.equal(validMediaResultDetails(available,"video","wan22-vace"),false);
  assert.equal(validMediaResultDetails({...available,image:"/pose.png"},"video","dwpose"),true);
  assert.equal(validMediaResultDetails({...available,image:"/result.png"},"image","flux-image"),true);
  assert.equal(validMediaResultDetails(available,"image","flux-image"),false);
  assert.equal(validMediaResultDetails({result_status:"partial"},"video","wan22-vace"),true);
});
