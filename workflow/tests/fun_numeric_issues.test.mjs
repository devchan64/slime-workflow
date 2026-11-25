import test from 'node:test';
import assert from 'node:assert/strict';
import {funNumericIssues} from '../../gui/funNumericIssues.mjs';

test('Fun Control 숫자 입력의 범위와 프레임 간격을 검증한다',()=>{
 const valid={frames:21,steps:4,seed:0,flow_shift:5,guidance_scale:1,switch_ratio:0.5};
 assert.deepEqual(Object.values(funNumericIssues(valid,81,2147483647)).filter(Boolean),[]);
 const errors=funNumericIssues({...valid,frames:22,steps:'',seed:-1,flow_shift:0,guidance_scale:11,switch_ratio:1},81,2147483647);
 assert.ok(Object.values(errors).every(Boolean));
 assert.ok(funNumericIssues({...valid,frames:85},81,2147483647).frames);
});
