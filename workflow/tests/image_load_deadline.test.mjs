import test from 'node:test';
import assert from 'node:assert/strict';
import {startImageLoadDeadline,startVisibleImageLoadDeadline} from '../../gui/imageLoadDeadline.mjs';

test('이미지 제한 시간은 한 번만 알리고 취소 후에는 알리지 않는다',()=>{
  const pending=[],timers={setTimeout(fn,ms){const timer={fn,ms};pending.push(timer);return timer;},clearTimeout(timer){timer.cleared=true;}};
  let count=0;
  const cancel=startImageLoadDeadline(()=>count++,timers);
  assert.equal(pending[0].ms,15000);pending[0].fn();pending[0].fn();assert.equal(count,1);
  cancel();assert.equal(pending[0].cleared,true);
  const stop=startImageLoadDeadline(()=>count++,timers);stop();pending[1].fn();assert.equal(count,1);
});

test('화면에 들어온 이미지에서만 제한 시간을 시작하고 취소하면 늦은 오류를 무시한다',()=>{
  const pending=[],timers={setTimeout(fn,ms){const timer={fn,ms};pending.push(timer);return timer;},clearTimeout(timer){timer.cleared=true;}};
  let observer,count=0;
  class Observer {constructor(callback){this.callback=callback;observer=this;}observe(element){this.element=element;}disconnect(){this.disconnected=true;}}
  const image={},cancel=startVisibleImageLoadDeadline(image,()=>count++,{Observer,timers});
  assert.equal(observer.element,image);
  observer.callback([{isIntersecting:false}]);assert.equal(pending.length,0);
  observer.callback([{isIntersecting:true}]);observer.callback([{isIntersecting:true}]);
  assert.equal(pending.length,1);assert.equal(pending[0].ms,15000);assert.equal(observer.disconnected,true);
  cancel();assert.equal(pending[0].cleared,true);pending[0].fn();assert.equal(count,0);
  const cancelBeforeVisible=startVisibleImageLoadDeadline(image,()=>count++,{Observer,timers});
  cancelBeforeVisible();observer.callback([{isIntersecting:true}]);assert.equal(pending.length,1);
  startVisibleImageLoadDeadline(image,()=>count++,{Observer,timers});observer.callback([{isIntersecting:true}]);
  pending[1].fn();pending[1].fn();assert.equal(count,1);
  assert.doesNotThrow(()=>startVisibleImageLoadDeadline(image,()=>count++,{Observer:null,timers})());
});
