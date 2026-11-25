import test from 'node:test';
import assert from 'node:assert/strict';
import {validBattlefieldState,battlefieldLoadFailed,sameBattlefieldState} from '../../gui/battlefieldState.mjs';
import {readFileSync} from 'node:fs';

test('전장 상태의 선택 목록과 현재 선택 및 표시 값을 확인한다',()=>{
  const state={choices:[['전체','all'],['전장','field-a']],field:'all',status:'준비됨',cameraReady:true,spawnRegionsVisible:false};
  assert.equal(validBattlefieldState(state),true);
  assert.equal(battlefieldLoadFailed(state),false);
  assert.equal(battlefieldLoadFailed({...state,cameraReady:false,status:'전장 로드 실패: 장면 준비 시간 초과'}),true);
  for(const value of [null,{...state,choices:[]},{...state,choices:[['전체','all'],['중복','all']]},{...state,choices:[['전체']]},{...state,choices:[['  ','all']]},{...state,choices:[['전체','  ']],field:'  '},{...state,field:'missing'},{...state,status:{}},{...state,cameraReady:'true'},{...state,spawnRegionsVisible:null}])
    assert.equal(validBattlefieldState(value),false);
});

test('표시 내용이 같으면 새 목록 객체도 같은 상태로 본다',()=>{
  const state={choices:[['전체','all'],['전장','field-a']],field:'all',status:'준비 중',cameraReady:false,spawnRegionsVisible:false};
  assert.equal(sameBattlefieldState(state,structuredClone(state)),true);
  for(const next of [{...state,field:'field-a'},{...state,status:'완료'},{...state,cameraReady:true},{...state,spawnRegionsVisible:true},{...state,choices:[['전장','field-a'],['전체','all']]},{...state,choices:[['수정','all'],['전장','field-a']]}])
    assert.equal(sameBattlefieldState(state,next),false);
  assert.equal(sameBattlefieldState(null,state),false);
});

test('게임에 등록된 전장 선택 목록과 초기 상태를 허용한다',()=>{
  const fixtures=JSON.parse(readFileSync(new URL('../../../slime-frontend/src/dev/battlefield-fixtures.json',import.meta.url),'utf8'));
  const choices=fixtures.map(({battle})=>[battle.field.name,battle.field.id]);
  assert.ok(choices.length>0);
  for(const [,field] of choices)
    assert.equal(validBattlefieldState({choices,field,status:'화면 준비 중',cameraReady:false,spawnRegionsVisible:false}),true);
  const runtime=readFileSync(new URL('../../../slime-frontend/review/battlefield-runtime.ts',import.meta.url),'utf8');
  assert.ok(runtime.includes('updateReviewStatus(`전장 로드 실패: ${currentFailureMessage}`)'));
});
