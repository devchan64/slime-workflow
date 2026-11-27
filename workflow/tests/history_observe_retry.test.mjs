import {test} from 'node:test';
import assert from 'node:assert/strict';
import {historyObserveRetry} from '../../gui/historyObserveRetry.mjs';

test('동시 조회 충돌만 재시도하고 최대 횟수를 지킨다',async()=>{
  let calls=0,waits=0;
  const read=async()=>{if(++calls<3)throw new Error('이 작업 저장소의 이력 조회가 이미 진행 중입니다.');return {records:[]};};
  assert.deepEqual(await historyObserveRetry(read,new AbortController().signal,async()=>{waits++;}),{records:[]});
  assert.equal(calls,3);assert.equal(waits,2);
  calls=0;
  await assert.rejects(historyObserveRetry(async()=>{calls++;throw new Error('다른 오류');},new AbortController().signal,async()=>{}),/다른 오류/);
  assert.equal(calls,1);
  calls=0;
  await assert.rejects(historyObserveRetry(async()=>{calls++;throw new Error('이력 조회가 이미 진행 중');},new AbortController().signal,async()=>{}),/이미 진행 중/);
  assert.equal(calls,3);
});

test('재시도 대기 중 취소하면 다음 조회를 시작하지 않는다',async()=>{
  const controller=new AbortController();let calls=0;
  const result=historyObserveRetry(async()=>{calls++;throw new Error('이력 조회가 이미 진행 중');},controller.signal,()=>{controller.abort();return new Promise(()=>{});});
  await assert.rejects(result);assert.equal(calls,1);
});

test('이미 취소된 조회는 첫 요청도 시작하지 않는다',async()=>{
  const controller=new AbortController();controller.abort();let calls=0;
  await assert.rejects(historyObserveRetry(async()=>{calls++;},controller.signal));
  assert.equal(calls,0);
});
