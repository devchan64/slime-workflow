import test from 'node:test';
import assert from 'node:assert/strict';
import {duplicateKeyframeFrames} from '../../gui/duplicateKeyframeFrames.mjs';

test('같은 출력 프레임을 숫자와 문자열 표현에 관계없이 찾는다',()=>{
  const duplicates=duplicateKeyframeFrames([{frame:'1'},{frame:1},{frame:'2'},{frame:''},{frame:'0'},{frame:'2.5'}]);
  assert.deepEqual([...duplicates],[1]);
  assert.equal(duplicateKeyframeFrames([{frame:''},{frame:' '},{frame:2}]).size,0);
});
