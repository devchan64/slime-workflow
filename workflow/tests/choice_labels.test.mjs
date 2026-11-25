import {test} from 'node:test';
import assert from 'node:assert/strict';
import {choiceLabels} from '../../gui/choiceLabels.mjs';

test('중복된 이름만 ID를 더하고 목록 순서와 선택 값을 유지한다',()=>{
  const choices=[['안개','fog-a'],['불꽃','fire'],['안개','fog-b']];
  assert.deepEqual(choiceLabels(choices),[['fog-a','안개 · fog-a'],['fire','불꽃'],['fog-b','안개 · fog-b']]);
  assert.deepEqual(choices,[['안개','fog-a'],['불꽃','fire'],['안개','fog-b']]);
  assert.deepEqual(choiceLabels([]),[]);
});

test('이름에 ID가 포함되어 표시 이름이 겹쳐도 각 선택지를 구분한다',()=>{
  const choices=[['숲','a'],['숲','b'],['숲 · a','c'],['숲 · a · 2','d']];
  const labels=choiceLabels(choices);
  assert.equal(new Set(labels.map(([,label])=>label)).size,choices.length);
  assert.deepEqual(labels.map(([id])=>id),['a','b','c','d']);
});
