import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import vm from 'node:vm';
import {installMapBrushControls} from '../../gui/ui/map/map-brush-controls.js';

test('지도 처리 중 새 브러시는 시작하지 않고 처리 후 다시 사용할 수 있다',()=>{
 const oldWindow=globalThis.window,oldDocument=globalThis.document,oldEvent=globalThis.CustomEvent;
 try{
  let captures=0,events=0;globalThis.window={mapReviewEditingEnabled:true,mapReviewBrushReadOnly:true,dispatchEvent:()=>events++};globalThis.document={querySelector:()=>({textContent:''})};globalThis.CustomEvent=class {constructor(type){this.type=type;}};
  const controls=installMapBrushControls({setPointerCapture:()=>captures++},()=>({column:1,row:2}));window.mapReviewBrushTool='raise';
  assert.equal(controls.beginBrushStroke({pointerId:1}),false);assert.equal(captures,0);assert.equal(window.mapReviewBrushQueue.length,0);
  window.mapReviewBrushReadOnly=false;assert.equal(controls.beginBrushStroke({pointerId:1}),true);assert.equal(window.mapReviewBrushActive,true);assert.equal(captures,1);controls.finishBrushStroke();assert.equal(window.mapReviewBrushActive,false);assert.equal(window.mapReviewBrushQueue.length,1);assert.equal(events,1);
 }finally{globalThis.window=oldWindow;globalThis.document=oldDocument;globalThis.CustomEvent=oldEvent;}
});
test('취소한 브러시 획은 대기열에 넣지 않고 입력 중 상태를 해제한다',()=>{
 const oldWindow=globalThis.window,oldDocument=globalThis.document;
 try{
  globalThis.window={mapReviewEditingEnabled:true};globalThis.document={querySelector:()=>({textContent:''})};
  const controls=installMapBrushControls({setPointerCapture:()=>{}},()=>({column:1,row:2}));window.mapReviewBrushTool='raise';
  controls.beginBrushStroke({pointerId:1});assert.equal(window.mapReviewBrushActive,true);
  controls.finishBrushStroke(true);assert.equal(window.mapReviewBrushActive,false);assert.equal(window.mapReviewBrushQueue.length,0);
 }finally{globalThis.window=oldWindow;globalThis.document=oldDocument;}
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
test('포인터 캡처가 예상 밖으로 해제돼도 입력된 획을 처리하고 잠금을 해제한다',()=>{
 const oldWindow=globalThis.window,oldDocument=globalThis.document,oldEvent=globalThis.CustomEvent;
 try{
  globalThis.window={mapReviewEditingEnabled:true,dispatchEvent:()=>{}};globalThis.document={querySelector:()=>({textContent:''})};globalThis.CustomEvent=class {};
  const canvas={setPointerCapture:()=>{},style:{}},controls=installMapBrushControls(canvas,()=>({column:1,row:2}));window.mapReviewBrushTool='raise';
  const source=readFileSync(new URL('../../gui/ui/map/block-map-review.js',import.meta.url),'utf8');
  const start=source.indexOf('currentMapCanvas.onpointerup='),end=source.indexOf('\n',start);
  let dragFinished=0;vm.runInNewContext(source.slice(start,end),{currentMapCanvas:canvas,currentBrushControls:controls,finishMapDrag:()=>dragFinished++});
  controls.beginBrushStroke({pointerId:1});canvas.onlostpointercapture({pointerId:1});
  assert.equal(window.mapReviewBrushActive,false);assert.equal(window.mapReviewBrushQueue.length,1);assert.equal(dragFinished,1);
  canvas.onlostpointercapture({pointerId:1});assert.equal(window.mapReviewBrushQueue.length,1);
 }finally{globalThis.window=oldWindow;globalThis.document=oldDocument;globalThis.CustomEvent=oldEvent;}
});
test('다른 포인터는 진행 중인 획을 덮어쓰거나 이동·종료하지 않는다',()=>{
 const oldWindow=globalThis.window,oldDocument=globalThis.document,oldEvent=globalThis.CustomEvent;
 try{
  let captures=0;globalThis.window={mapReviewEditingEnabled:true,dispatchEvent:()=>{}};globalThis.document={querySelector:()=>({textContent:''})};globalThis.CustomEvent=class {};
  const controls=installMapBrushControls({setPointerCapture:()=>captures++},event=>({column:event.pointerId,row:0}));window.mapReviewBrushTool='raise';
  controls.beginBrushStroke({pointerId:1});controls.beginBrushStroke({pointerId:2});controls.moveBrushStroke({pointerId:2});
  assert.equal(controls.finishBrushStroke(false,2),false);assert.equal(window.mapReviewBrushActive,true);assert.equal(captures,1);
  assert.equal(controls.finishBrushStroke(false,1),true);assert.equal(window.mapReviewBrushActive,false);
  assert.deepEqual(window.mapReviewBrushQueue[0].map(point=>point.column),[1]);
 }finally{globalThis.window=oldWindow;globalThis.document=oldDocument;globalThis.CustomEvent=oldEvent;}
});
test('획을 시작한 뒤 도구 설정이 바뀌어도 그 획에는 원래 설정을 적용한다',()=>{
 const oldWindow=globalThis.window,oldDocument=globalThis.document,oldEvent=globalThis.CustomEvent;
 try{
  globalThis.window={mapReviewEditingEnabled:true,dispatchEvent:()=>{}};globalThis.document={querySelector:()=>({textContent:''})};globalThis.CustomEvent=class {};
  const tools=[],controls=installMapBrushControls({setPointerCapture:()=>{}},(event,tool)=>{tools.push(tool);return {column:event.column,row:0};});
  Object.assign(window,{mapReviewBrushTool:'floor',mapReviewBrushTile:'a',mapReviewBrushWall:'wall-a',mapReviewBrushTexture:'asset-a'});
  controls.beginBrushStroke({pointerId:1,column:0});
  Object.assign(window,{mapReviewBrushTool:'wall',mapReviewBrushTile:'b',mapReviewBrushWall:'wall-b',mapReviewBrushTexture:'asset-b'});
  controls.moveBrushStroke({pointerId:1,column:1});controls.finishBrushStroke(false,1);
  assert.deepEqual(tools,['floor','floor']);
  assert.deepEqual(window.mapReviewBrushQueue[0].map(({tool,tile,wall,texture})=>[tool,tile,wall,texture]),[['floor','a','wall-a','asset-a'],['floor','a','wall-a','asset-a']]);
 }finally{globalThis.window=oldWindow;globalThis.document=oldDocument;globalThis.CustomEvent=oldEvent;}
});
