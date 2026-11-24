import test from 'node:test';
import assert from 'node:assert/strict';
import {formStateLabel} from '../../gui/minimaxFormState.mjs';

test('기존 접수의 성공·거부·불확실 상태를 구분한다',()=>{
  assert.equal(formStateLabel('external_receipt','accepted'),'기존 경로 접수됨');
  assert.equal(formStateLabel('external_receipt','rejected'),'기존 접수 거부됨');
  assert.equal(formStateLabel('external_receipt','unknown'),'기존 접수 확인 필요');
});
