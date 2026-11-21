import {test} from 'node:test';
import assert from 'node:assert/strict';
import {validateGenerationControlResponse as valid} from '../../gui/generationControlResponse.mjs';

test('중지 접수 여부와 선택 대상이 확인된 응답만 성공 처리한다', () => {
  assert.equal(valid('cancel','job-1',{status:'running',cancel_requested:true}),true);
  assert.equal(valid('cancel','job-1',{id:'job-1',cancel_requested:true}),true);
  for (const response of [null, {}, {cancel_requested:false}, {id:'job-2',cancel_requested:true}])
    assert.equal(valid('cancel','job-1',response),false);
});
test('재개는 요청한 작업의 대기 접수만 성공 처리한다', () => {
  assert.equal(valid('resume','job-1',{id:'job-1',status:'queued'}),true);
  for (const response of [null, {}, {id:'job-1',status:'failed'}, {id:'job-2',status:'queued'}, {status:'queued'}])
    assert.equal(valid('resume','job-1',response),false);
});
