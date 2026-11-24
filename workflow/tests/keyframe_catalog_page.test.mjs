import test from 'node:test';
import assert from 'node:assert/strict';
import {validKeyframeCatalogPage} from '../../gui/keyframeCatalogPage.mjs';

test('키프레임 페이지의 경계와 표시 필드를 확인한다',()=>{
  const item={id:'a'.repeat(32),tag:'서기',source_frame:1},snapshot='b'.repeat(64);
  const page={items:[item],total:1,offset:0,next_offset:null,snapshot,note:'안내'};
  assert.equal(validKeyframeCatalogPage(page,{}),true);
  for(const value of [{...page,note:{}},{...page,items:[{...item,source_frame:{}}]},{...page,items:[{...item,id:'bad'}]},{...page,next_offset:1}])
    assert.equal(validKeyframeCatalogPage(value,{}),false);
  assert.equal(validKeyframeCatalogPage({...page,items:[],total:0},{}),true);
});
