import test from 'node:test';
import assert from 'node:assert/strict';
import {progressDeadline} from '../../gui/progressDeadline.mjs';

test('진행은 제한 시간을 갱신하고 정리 후에는 타이머와 리스너가 남지 않는다', () => {
  const oldSet=globalThis.setTimeout, oldClear=globalThis.clearTimeout;
  const timers=new Map(); let next=0, expired=0;
  globalThis.setTimeout=(fn,delay)=>{assert.equal(delay,30000);timers.set(++next,fn);return next;};
  globalThis.clearTimeout=id=>timers.delete(id);
  try {
    const target=new EventTarget();
    const cancel=progressDeadline(target,'progress',()=>expired++);
    assert.deepEqual([...timers.keys()],[1]);
    target.dispatchEvent(new Event('progress'));
    assert.deepEqual([...timers.keys()],[2]);
    timers.get(2)();
    assert.equal(expired,1);
    cancel();
    target.dispatchEvent(new Event('progress'));
    assert.equal(timers.size,0);
  } finally {globalThis.setTimeout=oldSet;globalThis.clearTimeout=oldClear;}
});
