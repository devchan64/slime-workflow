import test from 'node:test';
import assert from 'node:assert/strict';
import {installSourceSizePreview} from '../ui/map/source-size-preview.js';

test('연속 저장은 성공한 공통 속성을 기대값으로 사용한다',()=>{
 globalThis.window={};
 const currentMapRecord={id:'sample',safeTown:false,spriteProperties:{grass:{anchorX:0.5,anchorY:0.94,groundFootprintColumns:1,groundFootprintRows:1,displayHeight:64}},objects:[{id:'one',textureKey:'grass',anchorX:0.5,anchorY:0.94,displayHeight:64}]};
 installSourceSizePreview({}, {},currentMapRecord,{tileWidth:160,tileHeight:80});
 const currentFirstPayload=window.mapSourceAnchorPayload('grass',0.5,0.9,1,1,57);
 window.mapSourceAnchorCommitted({saved:true,payload:currentFirstPayload});
 const currentNextPayload=window.mapSourceAnchorPayload('grass',0.5,0.9,1,1,60);
 assert.equal(currentNextPayload.expected.displayHeight,57);
 assert.equal(currentNextPayload.expected.anchorY,0.9);
 window.mapSourceAnchorCommitted({saved:false,payload:currentNextPayload});
 assert.equal(window.mapSourceAnchorRead('grass')[4],57);
 window.mapSourceAnchorCommitted({saved:true,payload:{...currentNextPayload,map:'another'}});
 assert.equal(window.mapSourceAnchorRead('grass')[4],57);
});

test('야외 미리보기는 표시 높이만 절반으로 그리고 저장 속성은 유지한다',async()=>{
 const currentDrawCalls=[];
 const currentPreviewContext={save(){},restore(){},setLineDash(){},translate(){},scale(){},clearRect(){},beginPath(){},moveTo(){},lineTo(){},closePath(){},fill(){},stroke(){},strokeRect(){},arc(){},drawImage(...currentDrawArguments){currentDrawCalls.push(currentDrawArguments);}};
 const currentPreviewCanvas={width:0,height:0,getContext:()=>currentPreviewContext};
 globalThis.window={};
 globalThis.location={href:'http://localhost/'};
 globalThis.document={querySelector:()=>currentPreviewCanvas,createElement:()=>({getContext:()=>({drawImage(){}})})};
 globalThis.Path2D=class {moveTo(){}lineTo(){}closePath(){}};
 globalThis.Image=class {width=200;height=300;async decode(){}};
 const currentSharedProperties={anchorX:.5,anchorY:.9,groundFootprintColumns:1,groundFootprintRows:1,displayHeight:120};
 const currentMapRecord={id:'preview',safeTown:false,spriteProperties:{rock:currentSharedProperties},objects:[{textureKey:'rock',...currentSharedProperties}]};
 try{
  for(const currentBillboardScale of [.5,1]){
   installSourceSizePreview({rock:{path:'/rock.png',source:'rock.png',sha256:'test'}},{rock:'rock'},currentMapRecord,{tileWidth:160*currentBillboardScale,tileHeight:80*currentBillboardScale,billboardScale:currentBillboardScale});
   await window.mapSourceResizePreview('rock',128);
   assert.deepEqual(currentDrawCalls.at(-1).slice(-2),[80*currentBillboardScale,120*currentBillboardScale]);
   assert.equal(window.mapSourceAnchorRead('rock')[4],120);
  }
 }finally{delete globalThis.Path2D;delete globalThis.document;delete globalThis.Image;delete globalThis.location;delete globalThis.window;}
});

test('공용 점유 미리보기는 짝수 접지 셀과 앵커 끝값에서도 이미지를 잘라내지 않는다',async()=>{
 const {drawAssetGroundPreview}=await import('../ui/map/source-size-preview.js');
 globalThis.Path2D=class {moveTo(){}lineTo(){}closePath(){}};
 const currentDrawCalls=[];
 const currentTranslationCalls=[];
 const currentPreviewContext={save(){},restore(){},setLineDash(){},translate(...currentTranslationValues){currentTranslationCalls.push(currentTranslationValues);},scale(){},clearRect(){},fill(){},stroke(){},strokeRect(){},beginPath(){},arc(){},drawImage(...currentImageArguments){currentDrawCalls.push(currentImageArguments);}};
 const currentPreviewCanvas={getContext:()=>currentPreviewContext};
 try{
  for(const currentAnchorValue of [0,.5,1]){
   const currentPreviewResult=drawAssetGroundPreview(currentPreviewCanvas,{width:256,height:128},{anchorX:currentAnchorValue,anchorY:currentAnchorValue,displayHeight:300,groundFootprintColumns:2,groundFootprintRows:1,billboardPlacementAnchor:'bottom'},{tileWidth:80,tileHeight:40,billboardScale:.5});
   assert.equal(currentPreviewResult.occupiedCells,2);
   const [,currentDrawLeft,currentDrawTop,currentImageWidth,currentImageHeight]=currentDrawCalls.at(-1);
   const currentImageLeft=currentDrawLeft+currentTranslationCalls.at(-2)[0]+currentTranslationCalls.at(-1)[0];
   const currentImageTop=currentDrawTop+currentTranslationCalls.at(-2)[1]+currentTranslationCalls.at(-1)[1];
   assert.ok(currentImageLeft>=0&&currentImageTop>=0);
   assert.ok(currentImageLeft+currentImageWidth<=currentPreviewCanvas.width);
   assert.ok(currentImageTop+currentImageHeight<=currentPreviewCanvas.height);
  }
 }finally{delete globalThis.Path2D;}
});


test('확대는 캔버스 폭과 저장 속성을 유지하고 높이를 맞춘다',async()=>{
 const {drawAssetGroundPreview}=await import('../ui/map/source-size-preview.js');
 const currentScaleCalls=[];
 const currentPreviewContext={save(){},restore(){},setLineDash(){},translate(){},scale(...currentScaleValues){currentScaleCalls.push(currentScaleValues);},clearRect(){},fill(){},stroke(){},strokeRect(){},beginPath(){},arc(){},drawImage(){}};
 const currentPreviewCanvas={getContext:()=>currentPreviewContext};
 const currentPropertyValues={anchorX:.5,anchorY:.75,displayHeight:64,groundFootprintColumns:1,groundFootprintRows:1,billboardPlacementAnchor:'top'};
 globalThis.Path2D=class {moveTo(){}lineTo(){}closePath(){}};
 try{
  let currentInitialSize;
  for(const currentPreviewZoom of [.5,1,1.5,2,4]){
   const currentPreviewResult=drawAssetGroundPreview(currentPreviewCanvas,{width:128,height:128},currentPropertyValues,{tileWidth:80,tileHeight:40,billboardScale:.5,previewZoom:currentPreviewZoom});
   currentInitialSize??=[currentPreviewCanvas.width,currentPreviewCanvas.height];
   assert.equal(currentPreviewCanvas.width,currentInitialSize[0]);
   assert.ok(currentPreviewCanvas.height>=currentInitialSize[1]);
   assert.deepEqual(currentScaleCalls.at(-1),[currentPreviewZoom,currentPreviewZoom]);
   assert.equal(currentPreviewResult.height,32);
   assert.equal(currentPropertyValues.displayHeight,64);
  }
 }finally{delete globalThis.Path2D;}
});
