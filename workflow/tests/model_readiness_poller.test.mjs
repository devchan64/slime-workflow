import test from 'node:test';
import assert from 'node:assert/strict';
import {startModelReadinessPoller} from '../../gui/modelReadinessPoller.mjs';

test('조회 실패 후 재시도해 정상 상태로 복구한다',async()=>{
  const events=[];let calls=0,stop;
  await new Promise((resolve,reject)=>{
    const guard=setTimeout(()=>reject(new Error('재조회 시간 초과')),1000);
    stop=startModelReadinessPoller({
      read:async()=>{calls++;if(calls===1)throw new Error('연결 실패');return {ready:true};},
      validate:value=>typeof value.ready==='boolean',delayForStatus:()=>null,initialRetryDelay:1,
      onStart:()=>events.push('start'),onFailure:error=>events.push(error.message),onFinish:()=>events.push('finish'),
      onSuccess:()=>{events.push('success');clearTimeout(guard);resolve();},timeoutMs:100,
    });
  });
  stop();
  assert.equal(calls,2);
  assert.deepEqual(events,['start','연결 실패','finish','start','success','finish']);
});

test('중단 신호를 무시하는 조회도 시간 초과로 복구하고 종료 후 응답을 무시한다',async()=>{
  let stop,signal,lateResolve,failures=0;
  await new Promise((resolve,reject)=>{
    const guard=setTimeout(()=>reject(new Error('시간 초과 미처리')),1000);
    stop=startModelReadinessPoller({
      read:current=>{signal=current;return new Promise(done=>{lateResolve=done;});},
      validate:()=>true,delayForStatus:()=>null,initialRetryDelay:null,
      onStart:()=>{},onSuccess:()=>reject(new Error('늦은 응답 적용')),
      onFailure:(_error,timedOut)=>{assert.equal(timedOut,true);failures++;clearTimeout(guard);resolve();},
      onFinish:()=>{},timeoutMs:5,
    });
  });
  stop();lateResolve({ready:true});await Promise.resolve();
  assert.equal(signal.aborted,true);assert.equal(failures,1);
});
