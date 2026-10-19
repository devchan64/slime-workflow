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
 const currentPreviewContext={clearRect(){},beginPath(){},moveTo(){},lineTo(){},closePath(){},fill(){},stroke(){},strokeRect(){},arc(){},drawImage(...currentDrawArguments){currentDrawCalls.push(currentDrawArguments);}};
 const currentPreviewCanvas={width:0,height:0,getContext:()=>currentPreviewContext};
 globalThis.window={};
 globalThis.location={href:'http://localhost/'};
 globalThis.document={querySelector:()=>currentPreviewCanvas,createElement:()=>({getContext:()=>({drawImage(){}})})};
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
 }finally{delete globalThis.document;delete globalThis.Image;delete globalThis.location;delete globalThis.window;}
});
