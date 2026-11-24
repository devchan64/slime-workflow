import test from 'node:test';
import assert from 'node:assert/strict';
import {isBuildVerificationFresh} from '../../gui/buildVerification.mjs';

test('빌드 등록은 30초 이내의 빌드 필요 확인만 허용한다',()=>{
  const value={record:{status:'rebuild_required'},checkedAt:1000};
  assert.equal(isBuildVerificationFresh(value,1000),true);
  assert.equal(isBuildVerificationFresh(value,30999),true);
  assert.equal(isBuildVerificationFresh(value,31000),false);
  assert.equal(isBuildVerificationFresh(value,999),false);
  assert.equal(isBuildVerificationFresh({...value,record:{status:'ready'}},2000),false);
  assert.equal(isBuildVerificationFresh(null,2000),false);
});
