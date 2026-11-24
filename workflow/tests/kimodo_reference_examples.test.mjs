import test from 'node:test';
import assert from 'node:assert/strict';
import {validKimodoReferenceExamples as valid} from '../../gui/kimodoReferenceExamples.mjs';

test('예시 목록과 참조 이미지 응답을 구분해 확인한다',()=>{
  assert.equal(valid([],false),true);
  assert.equal(valid([{id:'example',label:'예시'}],false),true);
  assert.equal(valid([{id:'example',label:'예시'},{id:'example',label:'다른 예시'}],false),false);
  assert.equal(valid([{name:'one.png',data:'YQ=='}],true),true);
  for(const value of [[],[{name:'one.png',data:''}],Array.from({length:9},()=>({name:'a',data:'YQ=='}))])assert.equal(valid(value,true),false);
});
