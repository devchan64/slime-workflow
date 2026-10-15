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

test('늦게 완료된 이전 시트는 최신 선택을 덮어쓰지 않고 로딩 중 적용을 막는다',async()=>{
 const {readFileSync}=await import('node:fs');
 const currentSourceText=readFileSync(new URL('../ui/character_animation/sprite-sheet-slicer.js',import.meta.url),'utf8');
 const currentLoadSource=currentSourceText.slice(currentSourceText.indexOf('async function loadSheetFile('),currentSourceText.indexOf('window.spriteSheetControls='));
 const currentPendingImages=[],currentRevokedUrls=[];
 class FixtureSheetImage{
  naturalWidth=64;naturalHeight=32;
  decode(){return new Promise((currentResolveLoad,currentRejectLoad)=>currentPendingImages.push({resolve:currentResolveLoad,reject:currentRejectLoad}));}
 }
 const currentWindowObject={spriteV2ValidateSheet:()=>({})};
 const currentHarnessFactory=new Function('Image','URL','window','collectSheetRectangles',`
 const SHEET_MAX_BYTES=32000000,SHEET_MAX_PIXELS=32000000;
 let currentSheetLoadSequence=0,currentSheetLoading=false,currentSheetImage=null,currentSheetName='',currentSheetBusy=false,currentHorizontalCuts=[],currentVerticalCuts=[];
 const drawSheetPreview=()=>{};
 ${currentLoadSource}
 return {load:loadSheetFile,name:()=>currentSheetName,readiness:window.spriteSheetReadiness};`);
 const currentHarnessRecord=currentHarnessFactory(FixtureSheetImage,{createObjectURL:currentFile=>currentFile.name,revokeObjectURL:currentUrl=>currentRevokedUrls.push(currentUrl)},currentWindowObject,collectSheetRectangles);
 const currentFirstLoad=currentHarnessRecord.load({name:'old',type:'image/png',size:1});
 const currentSecondLoad=currentHarnessRecord.load({name:'new',type:'image/png',size:1});
 assert.equal(currentHarnessRecord.readiness().applyReady,false);
 assert.match(currentHarnessRecord.readiness().reason,/로딩/);
 currentPendingImages[1].resolve();assert.equal(await currentSecondLoad,true);
 assert.equal(currentHarnessRecord.name(),'new');assert.equal(currentHarnessRecord.readiness().applyReady,true);
 currentPendingImages[0].resolve();assert.equal(await currentFirstLoad,false);
 assert.equal(currentHarnessRecord.name(),'new');assert.deepEqual(currentRevokedUrls,['old']);
 const currentFailedLoad=currentHarnessRecord.load({name:'broken',type:'image/png',size:1});
 currentPendingImages[2].reject(Error('decode failed'));await assert.rejects(currentFailedLoad,/decode failed/);
 assert.equal(currentHarnessRecord.name(),'new');assert.equal(currentHarnessRecord.readiness().applyReady,true);
 assert.deepEqual(currentRevokedUrls,['old','broken']);
});
