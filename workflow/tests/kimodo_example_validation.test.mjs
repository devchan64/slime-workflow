import test from 'node:test';
import assert from 'node:assert/strict';
import {validKimodoExample,validKimodoExampleList} from '../../gui/kimodoExampleValidation.mjs';

test('예시의 참조·구간·키프레임 형식을 확인한다',()=>{
  const example={label:'걷기',prompt:'walk',frames:30,settings:{},references:[{name:'a.png',data:'YQ=='}]};
  assert.equal(validKimodoExample(example),true);
  for(const value of [{...example,references:[{}]},{...example,frames:'30'},{...example,settings:{segment_frames:[{}]}},{...example,settings:{keyframes:[{id:'bad',frame:1}]}}])
    assert.equal(validKimodoExample(value),false);
});

test('예시 목록은 빈 목록을 허용하고 중복·손상된 표시 필드를 거부한다',()=>{
  const row={id:'walk',label:'걷기',prompt:'walk'};
  assert.equal(validKimodoExampleList([]),true);
  assert.equal(validKimodoExampleList([row]),true);
  for(const rows of [null,[row,row],[{...row,prompt:{}}],[{...row,id:''}]])assert.equal(validKimodoExampleList(rows),false);
});
