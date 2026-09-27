import {test} from 'node:test';
import assert from 'node:assert/strict';
import {createRequire} from 'node:module';
const loadSpriteCoreModule=createRequire(import.meta.url);
const {calculateSpriteDrawRectangle,createSpriteDefaultSettings,calculateSpritePointerPosition,createSpriteSheetLayout,validateSpriteFrameSettings}=loadSpriteCoreModule('../ui/character_animation/sprite-editor.js');
const sampleSourceFrame={frameId:'down_left.0',direction:'down_left',rect:{x:0,y:0,width:384,height:384},anchor:{x:192,y:374}};
test('384px 원본 배치는 발 기준점 때문에 위로 잘리지 않는다',()=>{
 const defaultFrameSettings=createSpriteDefaultSettings(sampleSourceFrame,384,{top:1,bottom:375});
 assert.deepEqual(calculateSpriteDrawRectangle(sampleSourceFrame,defaultFrameSettings,384),{x:0,y:0,width:384,height:384});
 const smallFrameSettings=createSpriteDefaultSettings(sampleSourceFrame,128,{top:1,bottom:375});
 assert.deepEqual(calculateSpriteDrawRectangle(sampleSourceFrame,smallFrameSettings,128),{x:0,y:0,width:128,height:128});
});
test('드래그 좌표는 512 상수가 아닌 실제 출력 크기를 사용한다',()=>{
 assert.deepEqual(calculateSpritePointerPosition({x:150,y:100},{left:50,top:50,width:192,height:192},384),{x:200,y:100});
 assert.deepEqual(calculateSpritePointerPosition({x:150,y:100},{left:50,top:50,width:192,height:192},128),{x:200/3,y:100/3});
});
test('16프레임 전체 내보내기는 시간순 4열·방향순 4행이다',()=>{
 const sourceDirectionNames=['down_left','down_right','up_left','up_right'];
 const sourceFrameRecords=sourceDirectionNames.flatMap(directionKeyName=>Array.from({length:4},(_,frameSequenceIndex)=>({...sampleSourceFrame,frameId:`${directionKeyName}.${frameSequenceIndex}`,direction:directionKeyName})));
 const outputSheetLayout=createSpriteSheetLayout(sourceFrameRecords,384);
 assert.deepEqual([outputSheetLayout.width,outputSheetLayout.height,outputSheetLayout.columns,outputSheetLayout.rows],[1536,1536,4,4]);
 assert.deepEqual(outputSheetLayout.frames.map(currentSheetCell=>[currentSheetCell.frame.frameId,currentSheetCell.x,currentSheetCell.y]),sourceDirectionNames.flatMap((directionKeyName,directionRowIndex)=>Array.from({length:4},(_,frameColumnIndex)=>[`${directionKeyName}.${frameColumnIndex}`,frameColumnIndex*384,directionRowIndex*384])));
 assert.equal(createSpriteSheetLayout(sourceFrameRecords.slice(0,4),384).height,384);
});
test('잘못된 좌표·배율·프레임 범위는 거절한다',()=>{
 const defaultFrameSettings=createSpriteDefaultSettings(sampleSourceFrame,384,{top:1,bottom:375});
 for(const invalidSettingPatch of [{scale:0},{scale:Infinity},{floor:0},{head:400},{x:NaN},{unknown:1}])assert.throws(()=>validateSpriteFrameSettings({...defaultFrameSettings,...invalidSettingPatch}));
 assert.throws(()=>createSpriteSheetLayout([],384));
 assert.throws(()=>createSpriteSheetLayout([{...sampleSourceFrame,direction:'unknown'}],384));
});
