import {test} from 'node:test';
import assert from 'node:assert/strict';
import {randomSeed} from '../../gui/randomSeed.mjs';
const source=(values)=>({getRandomValues(array){array[0]=values.shift();return array;}});
test('랜덤 시드는 허용 범위 전체를 사용하고 편향 구간은 재추첨한다',()=>{
  assert.equal(randomSeed(2147483647,source([4294967295])),2147483647);
  assert.equal(randomSeed(4294967295,source([4294967295])),4294967295);
  assert.equal(randomSeed(5,source([4294967295,11])),5);
  assert.equal(randomSeed(0,source([123])),0);
  assert.throws(()=>randomSeed(-1));
  assert.throws(()=>randomSeed(4294967296));
});
