import test from 'node:test';
import assert from 'node:assert/strict';
import {formatActivityCopy} from '../../gui/formatActivityCopy.mjs';
test('도구 활동의 대상, 결과, 제한과 식별자를 함께 복사한다',()=>{
 const value=formatActivityCopy({name:'terminal',target:'명령',call_id:'abc'}, {output:'오류',output_truncated:true,duration_ms:1200},'실패');
 for(const text of ['terminal','실패','명령','오류','앞부분만','1.2초','abc'])assert.ok(value.includes(text));
 assert.match(formatActivityCopy({name:'terminal'},null,'실행 중'),/아직 기록되지 않음/);
});
