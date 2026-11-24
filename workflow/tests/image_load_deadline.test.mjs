import test from 'node:test';
import assert from 'node:assert/strict';
import {startImageLoadDeadline} from '../../gui/imageLoadDeadline.mjs';

test('이미지 제한 시간은 한 번만 알리고 취소 후에는 알리지 않는다',()=>{
  const pending=[],timers={setTimeout(fn,ms){const timer={fn,ms};pending.push(timer);return timer;},clearTimeout(timer){timer.cleared=true;}};
  let count=0;
  const cancel=startImageLoadDeadline(()=>count++,timers);
  assert.equal(pending[0].ms,15000);pending[0].fn();pending[0].fn();assert.equal(count,1);
  cancel();assert.equal(pending[0].cleared,true);
  const stop=startImageLoadDeadline(()=>count++,timers);stop();pending[1].fn();assert.equal(count,1);
});
