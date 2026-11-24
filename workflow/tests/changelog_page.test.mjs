import test from 'node:test';
import assert from 'node:assert/strict';
import {validChangelogPage} from '../../gui/changelogPage.mjs';

test('변경 기록 응답은 요청한 페이지 또는 범위 조정된 마지막 페이지여야 한다',()=>{
  const page={date:'2026-11-24',content:'기록',index:1,count:3};
  assert.equal(validChangelogPage(page,1),true);
  assert.equal(validChangelogPage({...page,index:2},8),true);
  assert.equal(validChangelogPage({...page,index:0},1),false);
  assert.equal(validChangelogPage({...page,index:1},8),false);
  assert.equal(validChangelogPage({...page,date:null},1),true);
  assert.equal(validChangelogPage({...page,date:undefined},1),false);
  assert.equal(validChangelogPage({...page,count:0},1),false);
  assert.equal(validChangelogPage({...page,content:null},1),false);
});
