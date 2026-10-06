import test from 'node:test';
import assert from 'node:assert/strict';
import {createRequire} from 'node:module';
const currentModuleRequire=createRequire(import.meta.url);
const {createUniformBoundaries,validateSheetBoundaries,collectSheetRectangles,collectAppendNumbers}=currentModuleRequire('../ui/character_animation/sprite-sheet-slicer.js');
test('나누어 떨어지지 않는 원본을 빈틈 없이 행 우선 분할',()=>{
 const currentHorizontalCuts=createUniformBoundaries(1457,4),currentVerticalCuts=createUniformBoundaries(1080,2);
 const currentRectangles=collectSheetRectangles(currentHorizontalCuts,currentVerticalCuts);
 assert.equal(currentRectangles.length,8);
 assert.deepEqual(currentRectangles[0],{x:0,y:0,width:364,height:540});
 assert.equal(currentRectangles.at(-1).x+currentRectangles.at(-1).width,1457);
 assert.equal(currentRectangles.reduce((currentPixelTotal,currentRectangle)=>currentPixelTotal+currentRectangle.width*currentRectangle.height,0),1457*1080);
});
test('이동한 경계와 외곽 크롭 좌표로 분할',()=>{
 const currentHorizontalCuts=validateSheetBoundaries([10,400,1400],1457);
 assert.deepEqual(collectSheetRectangles(currentHorizontalCuts,[20,1000]),[{x:10,y:20,width:390,height:980},{x:400,y:20,width:1000,height:980}]);
});
test('역순·중복·범위 초과 및 과도한 프레임 거절',()=>{
 for(const currentInvalidCuts of [[0,0,100],[20,10],[0,101],[0,1.5,100]])assert.throws(()=>validateSheetBoundaries(currentInvalidCuts,100));
 assert.throws(()=>createUniformBoundaries(100,0));
 assert.throws(()=>collectSheetRectangles(createUniformBoundaries(100,16),createUniformBoundaries(100,16)));
});

test('여러 시트를 추가해도 기존 프레임 다음 번호부터 이어진다',()=>{
 assert.deepEqual(collectAppendNumbers(0,4),[1,2,3,4]);
 assert.deepEqual(collectAppendNumbers(4,4),[5,6,7,8]);
 assert.deepEqual(collectAppendNumbers(8,8),[9,10,11,12,13,14,15,16]);
});
