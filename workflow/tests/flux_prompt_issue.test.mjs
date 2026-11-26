import test from 'node:test';
import assert from 'node:assert/strict';
import {fluxPromptIssue,fluxTranslationIssue} from '../../gui/fluxPromptIssue.mjs';

test('번역 설명과 한국어 프롬프트의 조합만 일반 프로필에서 제한한다',()=>{
  const both={prompt:'붉은 집',translation_source_ko:'숲속의 집'};
  assert.ok(fluxPromptIssue(both,'flux-image'));
  assert.equal(fluxPromptIssue({...both,prompt:'red house'},'flux-image'),'');
  assert.equal(fluxPromptIssue({...both,translation_source_ko:''},'flux-image'),'');
  assert.equal(fluxPromptIssue({...both,prompt:''},'flux-image'),'');
  assert.equal(fluxPromptIssue(both,'flux-building'),'');
  assert.equal(fluxPromptIssue(both,'flux-expression'),'');
});

test('번역 설명은 비어 있거나 6000자 이하이며 한글을 포함해야 한다',()=>{
  const form=translation_source_ko=>({translation_source_ko});
  for (const service of ['flux-image','flux-expression']) {
    assert.equal(fluxTranslationIssue(form('  '),service),'');
    assert.equal(fluxTranslationIssue(form('설명 ' + 'a'.repeat(5997)),service),'');
    assert.ok(fluxTranslationIssue(form('설명 ' + 'a'.repeat(5998)),service));
    assert.ok(fluxTranslationIssue(form('English only'),service));
  }
  assert.equal(fluxTranslationIssue(form('English only'),'flux-building'),'');
});
