import test from 'node:test';
import assert from 'node:assert/strict';
import {sessionQueueStateLabel,validSessionQueueResult} from '../../gui/sessionQueueValidation.mjs';

test('세션 작업 목록은 표시와 결과 선택에 필요한 필드를 확인한다',()=>{
  const step={run_id:'run',step_id:'step',request_id:'request',generator:null,state:'waiting',source_state:null,source_job_id:null,created_at:null,observed_at:null};
  const direct={request_id:'direct',generator:'flux-image',state:'queued',source_kind:'flux_proposal',source_job_id:null};
  assert.equal(validSessionQueueResult({steps:[step],direct_jobs:[direct]}),true);
  for(const bad of [{steps:[{...step,state:{}}]}, {steps:[{...step,run_id:null}]}, {steps:[],direct_jobs:[{...direct,generator:[]}]}, {steps:[],direct_jobs:{}}])
    assert.equal(validSessionQueueResult(bad),false);
  assert.equal(sessionQueueStateLabel({queued:'대기'},'queued'),'대기');
  assert.equal(sessionQueueStateLabel({queued:'대기'},'toString'),'toString');
});
