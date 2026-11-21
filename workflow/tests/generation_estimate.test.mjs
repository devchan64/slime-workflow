import {test} from 'node:test';
import assert from 'node:assert/strict';
import {validGenerationEstimate} from '../../gui/generationEstimate.mjs';
const base={remaining:null,completion:null,total_seconds:null,estimated_progress:null,sample_count:0,updated_at:'2026-11-21T12:00:00+09:00',scope:'추론',basis:'표본 대기'};
test('서비스 추정이 미정이거나 유효한 실측값일 때만 표시한다',()=>{
 assert.equal(validGenerationEstimate(base),true);
 assert.equal(validGenerationEstimate({...base,remaining:30,total_seconds:60,estimated_progress:50,completion:'2026-11-21T12:00:30+09:00',sample_count:2}),true);
 for(const invalid of [{remaining:-1},{total_seconds:Infinity},{estimated_progress:100},{total_seconds:0},{updated_at:'2026-11-21T12:00:00'},{completion:'2026-11-21T12:00:30'},{sample_count:-1},{updated_at:'bad'},{completion:'bad'},{scope:null},{remaining:undefined}])
   assert.equal(validGenerationEstimate({...base,...invalid}),false);
});
