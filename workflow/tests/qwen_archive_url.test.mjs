import {test} from 'node:test';
import assert from 'node:assert/strict';
import {qwenArchiveUrl} from '../../gui/qwenArchiveUrl.mjs';

test('보관 결과를 열고 닫을 때 서비스·세션과 주소 조각을 유지한다',()=>{
  const original='http://localhost/management/assistant/qwen-archive/?service=qwen&session=s1&job=old#history';
  const opened=qwenArchiveUrl(original,'new');
  assert.equal(opened.searchParams.get('job'),'new');assert.equal(opened.searchParams.get('service'),'qwen');assert.equal(opened.searchParams.get('session'),'s1');assert.equal(opened.hash,'#history');
  const closed=qwenArchiveUrl(opened.href,'');assert.equal(closed.searchParams.has('job'),false);assert.equal(closed.searchParams.get('session'),'s1');assert.equal(closed.hash,'#history');
});
