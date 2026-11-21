import {test} from 'node:test';
import assert from 'node:assert/strict';
import {countPromptWords} from '../../gui/promptWords.mjs';
test('프롬프트 단어 수는 연속 공백과 줄바꿈을 구분자로 센다',()=>{
  assert.equal(countPromptWords(''),0);
  assert.equal(countPromptWords(' \n\t '),0);
  assert.equal(countPromptWords(' one  둘\nthree\tfour '),4);
  assert.equal(countPromptWords('한글 문장'),2);
});
