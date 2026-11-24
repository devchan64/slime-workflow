import test from 'node:test';
import assert from 'node:assert/strict';
import {readHandoffHistoryResult} from '../../gui/handoffHistoryResult.mjs';

test('양도 이력은 같은 세션·고유 ID·조회 중 변경 여부를 확인한다',()=>{
  const row={id:'request_123',service:'kimodo',session_id:'session',state:'running'};
  const result={session_id:'session',handoffs:[row]};
  assert.deepEqual(readHandoffHistoryResult(result,'session',2,2),[row]);
  assert.deepEqual(readHandoffHistoryResult({session_id:'session',handoffs:[]},'session',2,2),[]);
  assert.throws(()=>readHandoffHistoryResult(result,'other',2,2),/일치하지/);
  assert.throws(()=>readHandoffHistoryResult({...result,handoffs:[row,row]},'session',2,2),/형식 오류/);
  assert.throws(()=>readHandoffHistoryResult(result,'session',2,3),/조회 중 양도 상태가 변경/);
  assert.throws(()=>readHandoffHistoryResult({...result,handoffs:[{...row,session_id:'other'}]},'session',2,2),/일치하지/);
});
