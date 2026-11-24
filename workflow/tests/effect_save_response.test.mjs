import test from 'node:test';
import assert from 'node:assert/strict';
import {validEffectSaveResponse,effectSaveNotice,effectSaveFailure} from '../../gui/effectSaveResponse.mjs';

test('이펙트 저장은 저장 상태와 리비전·세대가 확인된 응답만 성공 처리한다',()=>{
  const valid={saved:true,revision:'a'.repeat(64),generation:12,snapshot:'pending'};
  assert.equal(validEffectSaveResponse(valid),true);
  assert.match(effectSaveNotice(valid),/저장 당시 원장 반영 대기/);
  assert.match(effectSaveNotice({...valid,snapshot:undefined}),/원장 반영 상태는 아래에서/);
  for(const value of [null,{...valid,saved:false},{...valid,revision:'bad'},{...valid,revision:{}},{...valid,generation:-1},{...valid,generation:'12'}])
    assert.equal(validEffectSaveResponse(value),false);
});

test('전송 전 실패와 전송 후 결과 불확실을 구분한다',()=>{
  assert.match(effectSaveFailure(new Error('준비 오류'),false),/요청을 보내지 못했습니다/);
  assert.doesNotMatch(effectSaveFailure(new Error('준비 오류'),false),/원본과 이력/);
  assert.match(effectSaveFailure(new Error('응답 오류'),true),/원본과 이력을 확인/);
});
