import {test} from 'node:test';
import assert from 'node:assert/strict';
import {installMapBrushControls} from '../../gui/ui/map/map-brush-controls.js';

test('지도 처리 중 새 브러시는 시작하지 않고 처리 후 다시 사용할 수 있다',()=>{
 const oldWindow=globalThis.window,oldDocument=globalThis.document,oldEvent=globalThis.CustomEvent;
 try{
  let captures=0,events=0;globalThis.window={mapReviewEditingEnabled:true,mapReviewBrushReadOnly:true,dispatchEvent:()=>events++};globalThis.document={querySelector:()=>({textContent:''})};globalThis.CustomEvent=class {constructor(type){this.type=type;}};
  const controls=installMapBrushControls({setPointerCapture:()=>captures++},()=>({column:1,row:2}));window.mapReviewBrushTool='raise';
  assert.equal(controls.beginBrushStroke({pointerId:1}),false);assert.equal(captures,0);assert.equal(window.mapReviewBrushQueue.length,0);
  window.mapReviewBrushReadOnly=false;assert.equal(controls.beginBrushStroke({pointerId:1}),true);assert.equal(captures,1);controls.finishBrushStroke();assert.equal(window.mapReviewBrushQueue.length,1);assert.equal(events,1);
 }finally{globalThis.window=oldWindow;globalThis.document=oldDocument;globalThis.CustomEvent=oldEvent;}
});
test('지도 처리 중 잠금은 이미 시작한 획을 버리지 않는다',()=>{
 const oldWindow=globalThis.window,oldDocument=globalThis.document,oldEvent=globalThis.CustomEvent;
 try{
  let events=0;globalThis.window={mapReviewEditingEnabled:true,mapReviewBrushReadOnly:false,dispatchEvent:()=>events++};globalThis.document={querySelector:()=>({textContent:''})};globalThis.CustomEvent=class {constructor(type){this.type=type;}};
  const controls=installMapBrushControls({setPointerCapture:()=>{}},()=>({column:2,row:3}));window.mapReviewBrushTool='raise';
  assert.equal(controls.beginBrushStroke({pointerId:1}),true);window.mapReviewBrushReadOnly=true;assert.equal(controls.finishBrushStroke(),true);
  assert.equal(window.mapReviewBrushQueue.length,1);assert.deepEqual(window.mapReviewBrushQueue[0].map(item=>[item.column,item.row,item.tool]),[[2,3,'raise']]);assert.equal(events,1);
  assert.equal(controls.beginBrushStroke({pointerId:2}),false);
 }finally{globalThis.window=oldWindow;globalThis.document=oldDocument;globalThis.CustomEvent=oldEvent;}
});
