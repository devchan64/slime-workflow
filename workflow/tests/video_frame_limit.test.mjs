import {test} from 'node:test';
import assert from 'node:assert/strict';
import {videoFrameLimit,validAnimateVideoInfo} from '../../gui/videoFrameLimit.mjs';

test('Animate-2 영상 정보는 표시와 출력 상한에 필요한 값을 검증한다',()=>{
  const valid={width:832,height:480,fps:30,frame_count:30,maximum_frames:13};
  assert.equal(validAnimateVideoInfo(valid),true);
  for(const invalid of [null,{...valid,fps:NaN},{...valid,width:0},{...valid,frame_count:'30'},{...valid,maximum_frames:12},{...valid,maximum_frames:85},{...valid,fps:121}])
    assert.equal(validAnimateVideoInfo(invalid),false);
  assert.equal(validAnimateVideoInfo(valid),true);
});

test('영상과 마스크를 모두 검사한 뒤 짧은 영상의 길이를 공통 상한으로 쓴다',()=>{
  assert.equal(videoFrameLimit([],{}),null);
  assert.equal(videoFrameLimit(['video','mask'],{video:{maximum_frames:81}}),null);
  assert.equal(videoFrameLimit(['video','mask'],{video:{maximum_frames:81},mask:{maximum_frames:41}}),41);
  assert.equal(videoFrameLimit(['video'],{video:{maximum_frames:65}}),65);
  assert.equal(videoFrameLimit(['video'],{video:{maximum_frames:0}}),null);
  assert.equal(videoFrameLimit(['video'],{video:{maximum_frames:'65'}}),null);
});
