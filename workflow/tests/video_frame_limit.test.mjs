import {test} from 'node:test';
import assert from 'node:assert/strict';
import {videoFrameLimit} from '../../gui/videoFrameLimit.mjs';

test('영상과 마스크를 모두 검사한 뒤 짧은 영상의 길이를 공통 상한으로 쓴다',()=>{
  assert.equal(videoFrameLimit([],{}),null);
  assert.equal(videoFrameLimit(['video','mask'],{video:{maximum_frames:81}}),null);
  assert.equal(videoFrameLimit(['video','mask'],{video:{maximum_frames:81},mask:{maximum_frames:41}}),41);
  assert.equal(videoFrameLimit(['video'],{video:{maximum_frames:65}}),65);
  assert.equal(videoFrameLimit(['video'],{video:{maximum_frames:0}}),null);
  assert.equal(videoFrameLimit(['video'],{video:{maximum_frames:'65'}}),null);
});
