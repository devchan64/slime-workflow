import test from 'node:test';
import assert from 'node:assert/strict';
import {initialMotionPlaying} from '../../gui/initialMotionPlaying.mjs';

test('동작 줄이기 설정을 존중하고 설정을 읽을 수 없으면 기존 기본값을 사용한다',()=>{
  const environment={matchMedia(query){assert.equal(this,environment);assert.equal(query,'(prefers-reduced-motion: reduce)');return {matches:true};}};
  assert.equal(initialMotionPlaying(environment),false);
  assert.equal(initialMotionPlaying({matchMedia:()=>({matches:false})}),true);
  assert.equal(initialMotionPlaying({}),true);
  assert.equal(initialMotionPlaying({matchMedia(){throw new Error('unsupported');}}),true);
});
