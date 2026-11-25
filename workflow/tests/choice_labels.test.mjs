import {test} from 'node:test';
import assert from 'node:assert/strict';
import {choiceLabels} from '../../gui/choiceLabels.mjs';

test('중복된 이름만 ID를 더하고 목록 순서와 선택 값을 유지한다',()=>{
  const choices=[['안개','fog-a'],['불꽃','fire'],['안개','fog-b']];
  assert.deepEqual(choiceLabels(choices),[['fog-a','안개 · fog-a'],['fire','불꽃'],['fog-b','안개 · fog-b']]);
  assert.deepEqual(choices,[['안개','fog-a'],['불꽃','fire'],['안개','fog-b']]);
  assert.deepEqual(choiceLabels([]),[]);
});
