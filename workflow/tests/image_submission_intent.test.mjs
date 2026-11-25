import {test} from 'node:test';
import assert from 'node:assert/strict';
import {imageSubmissionIntent} from '../../gui/imageSubmissionIntent.mjs';

test('standalone affirmative image instructions use the submission path',()=>{
  for(const text of ['생성한다.','생성해 주세요!','생성하자','생성합니다','GPU 양도에 동의.'])assert.equal(imageSubmissionIntent(text),true);
  for(const text of ['생성하지 마','생성할까요?','생성해도 되나요?','사과를 생성해','생성한다. 취소','GPU 양도에 동의하지 않음'])assert.equal(imageSubmissionIntent(text),false);
});
