import {test} from "node:test";
import assert from "node:assert/strict";
import {validMapDraftPreview,mapDraftSaveReason,isMapCellDirty,invalidMapCellHeight,readMapCell} from "../../gui/mapDraftPreview.mjs";

test("셀 높이는 0~20 정수만 허용한다",()=>{
  for(const value of [0,20,'0','20'])assert.equal(invalidMapCellHeight(value),false);
  for(const value of ['',null,-1,21,1.5,'abc'])assert.equal(invalidMapCellHeight(value),true);
});

test("셀 좌표와 원본 응답을 함께 확인한다",()=>{
  const snapshot={map:"field",revision:"rev",tiles:{rows:["ab","ba"],objects:[]},terrain:{elevations:[[0,1],[2,3]],blocked:[[1,0]]},codes:{a:"땅",b:"벽"}};
  assert.deepEqual(readMapCell(snapshot,"field",{column:1,row:0}),{column:1,row:0,tile:"b",height:1,blocked:true});
  assert.throws(()=>readMapCell(snapshot,"field",{column:2,row:0}),/범위/);
  assert.throws(()=>readMapCell(snapshot,"field",{column:0,row:-1}),/범위/);
  assert.throws(()=>readMapCell({...snapshot,terrain:{...snapshot.terrain,blocked:[null]}},"field",{column:0,row:0}),/형식/);
  assert.throws(()=>readMapCell({...snapshot,codes:{}},"field",{column:0,row:0}),/원본 정보/);
});

test("셀의 입력 변경은 숫자 표현을 정규화해 판단한다",()=>{
  const original={tile:"a",height:1,blocked:false};
  assert.equal(isMapCellDirty({...original,height:"1"},original),false);
  assert.equal(isMapCellDirty({...original,height:""},original),true);
  assert.equal(isMapCellDirty({...original,blocked:true},original),true);
  assert.equal(isMapCellDirty({...original,wall:"stone"},original),true);
});

test("지도 초안은 저장 가능 여부와 차단 이유를 구분한다",()=>{
  const preview={changed:true,save_available:true,save_block_reason:null,token:"a".repeat(64),render:{},cells:1,reachable:10};
  assert.equal(validMapDraftPreview(preview),true);
  assert.equal(mapDraftSaveReason(preview),"");
  assert.match(mapDraftSaveReason({...preview,changed:false}),/변경된 내용/);
  assert.match(mapDraftSaveReason({...preview,save_available:false,save_block_reason:"database"}),/데이터베이스/);
  assert.match(mapDraftSaveReason({...preview,save_available:false,save_block_reason:"interrupted"}),/복구/);
  assert.equal(validMapDraftPreview({...preview,save_available:"false"}),false);
  assert.equal(validMapDraftPreview({...preview,render:null}),false);
});
