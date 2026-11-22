import assert from 'node:assert/strict';
import {observedGenerationProgress,validInferenceCompletion} from '../../gui/generationProgressModel.mjs';
const worker={stage:'inference',step:3,total:20,updated_at:'2026-11-22T14:45:00+09:00',scope:'추론 단계'};
assert.deepEqual(observedGenerationProgress({worker_progress:worker}),{stage:'inference',step:3,total:20,updatedAt:worker.updated_at,scope:'추론 단계'});
assert.equal(observedGenerationProgress({worker_progress:{...worker,step:21}}),null);
assert.equal(observedGenerationProgress({worker_progress:null}),null);
const event={'generation.stage':'inference','generation.step':4,'generation.step.total':20,'generation.updated_at':worker.updated_at};
assert.equal(observedGenerationProgress({progress_event:event,worker_progress:worker}).step,4);
assert.equal(observedGenerationProgress({progress_event:{...event,'generation.step':-1},worker_progress:worker}).step,3);

assert.equal(observedGenerationProgress({progress_event:event}).estimate,null);
const estimated={...event,'generation.estimate.basis':'추론 단계 표본','generation.estimate.scope':'추론 단계','generation.estimate.sample_count':2,'generation.estimate.remaining_seconds':120,'generation.estimate.completion_time':'2026-11-22T14:47:00+09:00'};
assert.equal(observedGenerationProgress({progress_event:estimated}).estimate.samples,2);
assert.equal(observedGenerationProgress({progress_event:{...estimated,'generation.estimate.sample_count':-1}}).estimate,null);

assert.equal(validInferenceCompletion('2026-11-22T14:47:00+09:00'),true);
assert.equal(validInferenceCompletion('2026-11-22T05:47:00Z'),true);
assert.equal(validInferenceCompletion('2026-11-22T14:47:00'),false);
assert.equal(validInferenceCompletion('not-a-date'),false);
assert.equal(validInferenceCompletion(null),false);
assert.equal(observedGenerationProgress({progress_event:{...estimated,'generation.estimate.scope':'  '}}).estimate,null);
assert.equal(observedGenerationProgress({progress_event:{...estimated,'generation.estimate.sample_count':Number.MAX_SAFE_INTEGER+1}}).estimate,null);
