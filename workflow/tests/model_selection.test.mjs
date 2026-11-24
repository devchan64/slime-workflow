import test from 'node:test';
import assert from 'node:assert/strict';
import {resolveModelSelection} from '../../gui/modelSelection.mjs';

test('모델 재조회는 선택을 유지하고 없어진 선택은 알린다',()=>{
  const models=[{id:'a'},{id:'b'}];
  assert.deepEqual(resolveModelSelection(models,'',''),{selected:'a',missing:''});
  assert.deepEqual(resolveModelSelection(models,'','b'),{selected:'b',missing:''});
  assert.deepEqual(resolveModelSelection(models,'b','a'),{selected:'b',missing:''});
  assert.deepEqual(resolveModelSelection(models,'removed',''),{selected:'',missing:'removed'});
  assert.deepEqual(resolveModelSelection(models,'','removed'),{selected:'',missing:'removed'});
  assert.deepEqual(resolveModelSelection([],'a',''),{selected:'',missing:'a'});
});
