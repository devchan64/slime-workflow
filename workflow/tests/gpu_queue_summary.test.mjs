import test from 'node:test';
import assert from 'node:assert/strict';
import {formatGpuQueueSummary} from '../../gui/gpuQueueSummary.mjs';

test('GPU 확인 불가와 대기 작업 수·목록 잘림을 구분한다',()=>{
  const data={jobs:[{id:'job-1',service:'kimodo'}],gpu_status:{status:'unavailable'}};
  assert.deepEqual(formatGpuQueueSummary(data),{text:'GPU 상태 확인 불가 · 대기 작업 1건',unavailable:true});
  assert.equal(formatGpuQueueSummary({...data,truncated:true}).text,'GPU 상태 확인 불가 · 대기 작업 1건 이상');
  assert.equal(formatGpuQueueSummary({jobs:[],gpu_status:{status:'idle'}}).text,'GPU 유휴 · 대기 작업 0건');
  assert.throws(()=>formatGpuQueueSummary({...data,jobs:[null]}));
  assert.throws(()=>formatGpuQueueSummary({...data,jobs:[{id:'job-1'}]}));
  assert.throws(()=>formatGpuQueueSummary({...data,truncated:'yes'}));
});
