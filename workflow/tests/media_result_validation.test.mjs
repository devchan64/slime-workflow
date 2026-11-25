import {test} from "node:test";
import assert from "node:assert/strict";
import {mediaResultErrorMessage,mediaResultPendingMessage,validMediaResultDetails} from "../../gui/mediaResultValidation.mjs";

test('메시지가 없는 비정상 오류도 복구 가능한 문자열로 표시한다',()=>{
  for(const problem of [null,undefined,'실패',{}, {message:42},{message:'  '}])assert.equal(mediaResultErrorMessage(problem,'다시 확인하세요'),'다시 확인하세요');
  assert.equal(mediaResultErrorMessage(new Error('조회 오류'),'다시 확인하세요'),'조회 오류');
  assert.equal(mediaResultErrorMessage(new TypeError('Failed to fetch'),'다시 확인하세요'),'다시 확인하세요');
});

test('결과 미준비는 진행 중과 종료 후를 구분하고 파일 확인 실패와 중복하지 않는다',()=>{
  for(const status of ['queued','running'])assert.match(mediaResultPendingMessage({status,result_status:'not_ready'}),/진행 상태/);
  for(const status of ['failed','cancelled','canceled','paused'])assert.match(mediaResultPendingMessage({status,result_status:'not_ready'}),/표시할 수 없습니다.*작업 상태와 이력/);
  for(const status of ['completed','unknown'])assert.match(mediaResultPendingMessage({status,result_status:'not_ready'}),/아직 준비되지 않았습니다.*작업 상태와 이력/);
  assert.equal(mediaResultPendingMessage({status:'running',result_status:'not_ready',file_observation:'unavailable'}),'');
  assert.equal(mediaResultPendingMessage({status:'completed',result_status:'available'}),'');
});

test("재생 가능한 오디오 경로나 트랙이 있는 결과만 허용한다",()=>{
  const available={result_status:"available"};
  assert.equal(validMediaResultDetails({...available,audio:"/result.wav",tracks:[]},"audio"),true);
  assert.equal(validMediaResultDetails({...available,tracks:[{label:"원본",wav:"/result.wav"}]},"audio"),true);
  assert.equal(validMediaResultDetails({...available,tracks:[]},"audio"),false);
  assert.equal(validMediaResultDetails({...available,tracks:[{label:"원본",wav:""}]},"audio"),false);
  assert.equal(validMediaResultDetails({...available,tracks:[{label:" ",wav:"/result.wav"}]},"audio"),false);
  assert.equal(validMediaResultDetails({...available,tracks:[{label:"원본",wav:"/result.wav"},{label:"반주",wav:"/result.wav"}]},"audio"),false);
  assert.equal(validMediaResultDetails({...available,tracks:[{label:"원본",wav:"/original.wav"},{label:"반주",wav:"/instrumental.wav"}]},"audio"),true);
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
