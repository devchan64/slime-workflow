import test from 'node:test';
import assert from 'node:assert/strict';
import {imageRetryUrl} from '../../gui/imageRetryUrl.mjs';

test('재시도 주소는 데이터·블롭 원본과 URL 조각을 보존한다',()=>{
  assert.equal(imageRetryUrl('data:image/png;base64,YWJj',2),'data:image/png;base64,YWJj');
  assert.equal(imageRetryUrl('blob:https://example.test/abc',2),'blob:https://example.test/abc');
  assert.equal(imageRetryUrl('/image.png',2),'/image.png?retry=2');
  assert.equal(imageRetryUrl('/image.png?v=1#part',2),'/image.png?v=1&retry=2#part');
});
