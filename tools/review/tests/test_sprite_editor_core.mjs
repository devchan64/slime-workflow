import {test} from 'node:test';
import assert from 'node:assert/strict';
import {createRequire} from 'node:module';
const loadSpriteCoreModule=createRequire(import.meta.url);
const {upgradeSpriteProjectDocument,calculateSpriteOutputAnchor,calculateSpriteScaleNudge,calculateSpriteDrawRectangle,createSpriteDefaultSettings,calculateSpritePointerPosition,createSpriteSheetLayout,validateSpriteFrameSettings}=loadSpriteCoreModule('../ui/character_animation/sprite-editor.js');
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

test('크기 패드는 몸체 높이 1px만 바꾸고 기준점과 배치를 유지한다',()=>{
 const originalFrameSettings={center:192,head:2,floor:374,anchorX:197.5,anchorY:374,x:5.5,y:5,scale:1};
 const enlargedFrameSettings=calculateSpriteScaleNudge(originalFrameSettings,1);
 assert.ok(Math.abs((enlargedFrameSettings.floor-enlargedFrameSettings.head)*enlargedFrameSettings.scale-373)<1e-9);
 assert.deepEqual({...enlargedFrameSettings,scale:1},originalFrameSettings);
 assert.ok(Math.abs(calculateSpriteScaleNudge(enlargedFrameSettings,-1).scale-1)<1e-9);
 assert.throws(()=>calculateSpriteScaleNudge({...originalFrameSettings,scale:8},1));
 assert.throws(()=>calculateSpriteScaleNudge({...originalFrameSettings,scale:.01},-1));
});

test('등록 에셋을 다시 열면 런타임 앵커 정렬을 유지한다',()=>{
 const registeredFrameRecord={...sampleSourceFrame,anchor:{x:198,y:369}};
 const registeredFrameSettings=createSpriteDefaultSettings(registeredFrameRecord,384,{top:1,bottom:375},true);
 assert.equal(registeredFrameSettings.x,0);assert.equal(registeredFrameSettings.y,0);
 assert.equal(calculateSpriteDrawRectangle(registeredFrameRecord,registeredFrameSettings,384).x,-6);
 assert.equal(calculateSpriteDrawRectangle(registeredFrameRecord,registeredFrameSettings,384).y,-23);
 const scaledFrameSettings=createSpriteDefaultSettings(registeredFrameRecord,128,{top:1,bottom:375},true);
 assert.equal(calculateSpriteDrawRectangle(registeredFrameRecord,scaledFrameSettings,128).x,-2);
});

test('384px 출력의 앵커 아래 여백은 38px이며 발 끝이 셀 안에 남는다',()=>{
 const currentFrameRecord={...sampleSourceFrame,anchor:{x:204,y:346}};
 const currentFrameSettings=createSpriteDefaultSettings(currentFrameRecord,384,{top:2,bottom:375},true);
 const currentDrawRectangle=calculateSpriteDrawRectangle(currentFrameRecord,currentFrameSettings,384);
 assert.equal(calculateSpriteOutputAnchor(384).y,346);
 assert.equal(currentDrawRectangle.y+374,374);
 assert.equal(currentDrawRectangle.y+2,2);
});
test('기존 v2 저장본은 v3 변환 후 원래 배치를 유지한다',()=>{
 const currentProjectDocument={version:2,output:{cellSize:384,targetHeight:352},frames:{'down_left.0':{anchorX:192,anchorY:348,x:0,y:-5,scale:1}}};
 upgradeSpriteProjectDocument(currentProjectDocument);
 assert.equal(currentProjectDocument.version,3);
 assert.equal(calculateSpriteDrawRectangle(sampleSourceFrame,currentProjectDocument.frames['down_left.0'],384).y,369-348-5);
 const previousOffsetValue=currentProjectDocument.frames['down_left.0'].y;
 upgradeSpriteProjectDocument(currentProjectDocument);
 assert.equal(currentProjectDocument.frames['down_left.0'].y,previousOffsetValue);
});

test('적용 범위는 선택 프레임·현재 방향·전체를 구분하고 잘못된 범위를 거절한다',()=>{
 const {selectSpriteScopeFrames}=loadSpriteCoreModule('../ui/character_animation/sprite-editor.js');
 const currentFrameRecords=[sampleSourceFrame,{...sampleSourceFrame,frameId:'down_left.1'},{...sampleSourceFrame,frameId:'up_left.0',direction:'up_left'}];
 assert.deepEqual(selectSpriteScopeFrames(currentFrameRecords,'down_left.1','selected').map(currentFrameRecord=>currentFrameRecord.frameId),['down_left.1']);
 assert.equal(selectSpriteScopeFrames(currentFrameRecords,'down_left.1','direction').length,2);
 assert.equal(selectSpriteScopeFrames(currentFrameRecords,'down_left.1','clip').length,3);
 assert.throws(()=>selectSpriteScopeFrames(currentFrameRecords,'down_left.1','unknown'));
 assert.throws(()=>selectSpriteScopeFrames(currentFrameRecords,'missing','clip'));
});

test('일괄 변경은 다른 설정을 보존하고 실패하면 원본 전체를 유지한다',()=>{
 const {buildSpriteBatchSettings}=loadSpriteCoreModule('../ui/character_animation/sprite-editor.js');
 const currentFrameRecords=[sampleSourceFrame,{...sampleSourceFrame,frameId:'down_left.1'}];
 const currentDefaultSettings=createSpriteDefaultSettings(sampleSourceFrame,384,{top:1,bottom:375});
 const currentSettingsLookup={'down_left.0':{...currentDefaultSettings,x:2},'down_left.1':{...currentDefaultSettings,x:8}};
 const originalSettingsSnapshot=structuredClone(currentSettingsLookup);
 const nextSettingsLookup=buildSpriteBatchSettings(currentFrameRecords,currentSettingsLookup,currentFrameSettings=>({...currentFrameSettings,y:12}));
 assert.equal(nextSettingsLookup['down_left.0'].x,2);
 assert.equal(nextSettingsLookup['down_left.1'].x,8);
 assert.equal(nextSettingsLookup['down_left.1'].y,12);
 assert.throws(()=>buildSpriteBatchSettings(currentFrameRecords,currentSettingsLookup,currentFrameSettings=>({...currentFrameSettings,scale:currentFrameSettings.x===8?0:2})));
 assert.deepEqual(currentSettingsLookup,originalSettingsSnapshot);
});

test('바닥 정렬은 358px 몸체를 잘라내지 않고 원본 기준점을 유지한다',()=>{
 const {calculateSpriteFloorSettings}=loadSpriteCoreModule('../ui/character_animation/sprite-editor.js');
 const currentFrameSettings={center:192,head:17,floor:375,anchorX:192,anchorY:376,x:0,y:0,scale:1};
 const nextFrameSettings=calculateSpriteFloorSettings(currentFrameSettings,384,376);
 const nextDrawRectangle=calculateSpriteDrawRectangle(sampleSourceFrame,nextFrameSettings,384);
 assert.equal(nextDrawRectangle.y+375,376);
 assert.equal(nextDrawRectangle.y+17,18);
 assert.equal(nextFrameSettings.anchorY,376);
 assert.equal(nextFrameSettings.scale,1);
});

test('높이 맞춤은 중심과 발의 출력 위치를 유지한다',()=>{
 const {calculateSpriteHeightSettings}=loadSpriteCoreModule('../ui/character_animation/sprite-editor.js');
 const currentFrameSettings={center:190,head:17,floor:375,anchorX:192,anchorY:346,x:9,y:4,scale:1};
 const nextFrameSettings=calculateSpriteHeightSettings(currentFrameSettings,320);
 for(const [currentCoordinateKey,currentAnchorKey,currentOffsetKey] of [['center','anchorX','x'],['floor','anchorY','y']])assert.ok(Math.abs((currentFrameSettings[currentCoordinateKey]-currentFrameSettings[currentAnchorKey])*currentFrameSettings.scale+currentFrameSettings[currentOffsetKey]-(nextFrameSettings[currentCoordinateKey]-nextFrameSettings[currentAnchorKey])*nextFrameSettings.scale-nextFrameSettings[currentOffsetKey])<1e-8);
 assert.equal((nextFrameSettings.floor-nextFrameSettings.head)*nextFrameSettings.scale,320);
 assert.equal(nextFrameSettings.anchorY,346);
});




test('일부 프레임 선택은 방향과 무관하게 지정한 대상만 변경한다',()=>{
 const {selectSpriteScopeFrames,buildSpriteBatchSettings}=loadSpriteCoreModule('../ui/character_animation/sprite-editor.js');
 const currentFrameRecords=[sampleSourceFrame,{...sampleSourceFrame,frameId:'down_left.1'},{...sampleSourceFrame,frameId:'up_left.0',direction:'up_left'}];
 const selectedFrameRecords=selectSpriteScopeFrames(currentFrameRecords,'down_left.1','custom',['down_left.0','up_left.0']);
 assert.deepEqual(selectedFrameRecords.map(currentFrameRecord=>currentFrameRecord.frameId),['down_left.0','up_left.0']);
 assert.deepEqual(selectSpriteScopeFrames(currentFrameRecords,'down_left.0','custom',[]),[]);
 const currentDefaultSettings=createSpriteDefaultSettings(sampleSourceFrame,384,{top:1,bottom:375});
 const currentSettingsLookup=Object.fromEntries(currentFrameRecords.map(currentFrameRecord=>[currentFrameRecord.frameId,{...currentDefaultSettings}]));
 const nextSettingsLookup=buildSpriteBatchSettings(selectedFrameRecords,currentSettingsLookup,currentFrameSettings=>({...currentFrameSettings,x:12}));
 Object.assign(currentSettingsLookup,nextSettingsLookup);
 assert.equal(currentSettingsLookup['down_left.0'].x,12);
 assert.equal(currentSettingsLookup['up_left.0'].x,12);
 assert.equal(currentSettingsLookup['down_left.1'].x,currentDefaultSettings.x);
});


test('X 중심 정렬과 Y 바닥 정렬은 다른 축과 기준점·배율을 유지한다',()=>{
 const {calculateSpriteCenterSettings,calculateSpriteFloorSettings}=loadSpriteCoreModule('../ui/character_animation/sprite-editor.js');
 const currentFrameSettings={center:180,head:17,floor:375,anchorX:192,anchorY:346,x:11,y:24,scale:.8};
 const centerAlignedSettings=calculateSpriteCenterSettings(currentFrameSettings,384);
 assert.deepEqual({...centerAlignedSettings,x:11},currentFrameSettings);
 assert.ok(Math.abs(192+(180-192)*.8+centerAlignedSettings.x-192)<1e-8);
 const floorAlignedSettings=calculateSpriteFloorSettings(currentFrameSettings,384,376);
 assert.deepEqual({...floorAlignedSettings,y:24},currentFrameSettings);
 assert.ok(Math.abs(346+(375-346)*.8+floorAlignedSettings.y-376)<1e-8);
});
