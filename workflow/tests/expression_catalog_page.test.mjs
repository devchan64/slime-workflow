import test from 'node:test';
import assert from 'node:assert/strict';
import {validExpressionCatalogPage} from '../../gui/expressionCatalogPage.mjs';

test('표정 페이지의 스냅샷·다음 위치·중복 항목을 확인한다',()=>{
  const snapshot='a'.repeat(64),rows=Array.from({length:20},(_,index)=>({id:`item_${index}`,label:`표정 ${index}`}));
  const page={records:rows,total:21,offset:0,next_offset:20,snapshot};
  assert.equal(validExpressionCatalogPage(page,{}),true);
  assert.equal(validExpressionCatalogPage({records:[{id:'last',label:'마지막'}],total:21,offset:20,next_offset:null,snapshot},{offset:20,snapshot}),true);
  for(const invalid of [{...page,next_offset:null},{...page,snapshot:'bad'},{...page,records:[...rows.slice(0,19),rows[0]]},{...page,total:22,records:rows.slice(0,19)}])
    assert.equal(validExpressionCatalogPage(invalid,{}),false);
  assert.equal(validExpressionCatalogPage(page,{snapshot:'b'.repeat(64)}),false);
});
