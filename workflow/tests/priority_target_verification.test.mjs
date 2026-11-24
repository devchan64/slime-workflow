import test from 'node:test';
import assert from 'node:assert/strict';
import {verifyPriorityTarget} from '../../gui/verifyPriorityTarget.mjs';

test('대상 확인 시간 초과 뒤 늦은 응답이 와도 순서 변경을 보내지 않는다',async()=>{
  const controller=new AbortController();let finish,submitted=false;
  const attempt=(async()=>{await verifyPriorityTarget(()=>new Promise(resolve=>{finish=resolve;}),controller,10);submitted=true;})();
  await assert.rejects(attempt,/순서 변경 요청은 보내지 않았습니다/);
  finish();await new Promise(resolve=>setImmediate(resolve));assert.equal(submitted,false);
});

test('화면 종료로 중단하면 대상 확인이 성공하더라도 순서 변경을 보내지 않는다',async()=>{
  const controller=new AbortController();let finish,submitted=false;
  const attempt=(async()=>{await verifyPriorityTarget(()=>new Promise(resolve=>{finish=resolve;}),controller);submitted=true;})();
  await new Promise(resolve=>setImmediate(resolve));controller.abort();
  await assert.rejects(attempt,{name:'AbortError'});
  finish();await new Promise(resolve=>setImmediate(resolve));assert.equal(submitted,false);
});
