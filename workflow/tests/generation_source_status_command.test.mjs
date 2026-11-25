import {test} from 'node:test';
import assert from 'node:assert/strict';
import {generationSourceStatusCommand} from '../../gui/generationSourceStatusCommand.mjs';

test('진행 중 작업은 이미지와 영상 서비스의 원본 상태 경로를 구분한다',()=>{
  assert.equal(generationSourceStatusCommand('flux-image'),'hermes-flux-source-status');
  assert.equal(generationSourceStatusCommand('flux-character'),'hermes-flux-source-status');
  assert.equal(generationSourceStatusCommand('minimax-h3-image'),'hermes-image-source-status');
  assert.equal(generationSourceStatusCommand('music-heartmula'),'hermes-audio-source-status');
  assert.equal(generationSourceStatusCommand('sfx-dasheng-audiogen'),'hermes-audio-source-status');
  assert.equal(generationSourceStatusCommand('minimax-h3-i2v'),'hermes-video-source-status');
});
