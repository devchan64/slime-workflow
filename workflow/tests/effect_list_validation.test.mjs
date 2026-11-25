import test from 'node:test';
import assert from 'node:assert/strict';
import {validEffectList} from '../../gui/effectListValidation.mjs';

test('이펙트 목록은 빈 목록을 허용하고 잘못된 항목과 중복 ID를 거부한다',()=>{
  const item={id:'fog',name:'안개'};
  assert.equal(validEffectList({effects:[]}),true);
  assert.equal(validEffectList({effects:[item]}),true);
  for(const value of [null,{}, {effects:[item,item]}, {effects:[{id:'',name:'안개'}]}, {effects:[{id:'  ',name:'안개'}]}, {effects:[{id:'fog',name:'  '}]}, {effects:[{id:'fog',name:{}}]}])
    assert.equal(validEffectList(value),false);
});
