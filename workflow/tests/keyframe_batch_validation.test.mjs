import test from 'node:test';
import assert from 'node:assert/strict';
import {validKeyframeBatchResult as valid,validKeyframeBatchRequest} from '../../gui/keyframeBatchValidation.mjs';

test('배치와 각 원본 해시가 정확히 대응해야 한다',()=>{
  const id='a'.repeat(32),expected=[{id,frame:1},{id,frame:20}];
  const source={id,preview_sha256:'b'.repeat(64),source_sha256:'c'.repeat(64)};
  const result={placements:expected,sources:[source],skeleton_signature_sha256:'d'.repeat(64),note:'안내'};
  assert.equal(valid(result,expected),true);
  for(const invalid of [{...result,sources:[]},{...result,sources:[source,source]},{...result,sources:[{...source,id:'e'.repeat(32)}]},{...result,sources:[{...source,source_sha256:'bad'}]},{...result,placements:[expected[0],{id,frame:21}]},{...result,note:{}}])
    assert.equal(valid(invalid,expected),false);
});

test('복원할 배치는 유효한 ID와 중복 없는 범위 내 프레임이어야 한다',()=>{
  const id='a'.repeat(32),rows=[{id,frame:1},{id,frame:30}];
  assert.equal(validKeyframeBatchRequest(rows,30),true);
  for(const invalid of [[],[{id,frame:0}],[{id,frame:31}],[{id,frame:1},{id,frame:1}],[{id:'bad',frame:1}]])
    assert.equal(validKeyframeBatchRequest(invalid,30),false);
  assert.equal(validKeyframeBatchRequest(rows,'30'),false);
});
