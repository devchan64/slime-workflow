import test from 'node:test';
import assert from 'node:assert/strict';
import {validExpressionCatalogPage,firstExpressionPage,expressionCursorForQuery,resetExpressionQuery} from '../../gui/expressionCatalogPage.mjs';

test('표정 페이지의 스냅샷·다음 위치·중복 항목을 확인한다',()=>{
  const snapshot='a'.repeat(64),rows=Array.from({length:20},(_,index)=>({id:`item_${index}`,label:`표정 ${index}`}));
  const page={records:rows,total:21,offset:0,next_offset:20,snapshot};
  assert.equal(validExpressionCatalogPage(page,{}),true);
  assert.equal(validExpressionCatalogPage({records:[{id:'last',label:'마지막'}],total:21,offset:20,next_offset:null,snapshot},{offset:20,snapshot}),true);
  for(const invalid of [{...page,next_offset:null},{...page,snapshot:'bad'},{...page,records:[...rows.slice(0,19),rows[0]]},{...page,total:22,records:rows.slice(0,19)}])
    assert.equal(validExpressionCatalogPage(invalid,{}),false);
  assert.equal(validExpressionCatalogPage(page,{snapshot:'b'.repeat(64)}),false);
});

test('표정 검색 조건을 바꾸거나 다시 돌아와도 이전 검색의 페이지 커서를 쓰지 않는다',()=>{
 const old={query:'웃음',cursor:{offset:20,snapshot:'a'.repeat(64)}};
 assert.equal(expressionCursorForQuery(old,'웃음'),old.cursor);
 assert.equal(expressionCursorForQuery(old,'슬픔'),firstExpressionPage);
 const changed=resetExpressionQuery(old,'슬픔');
 assert.equal(expressionCursorForQuery(changed,'슬픔'),firstExpressionPage);
 assert.equal(expressionCursorForQuery(changed,'웃음'),firstExpressionPage);
 assert.equal(resetExpressionQuery(changed,'슬픔'),changed);
});
