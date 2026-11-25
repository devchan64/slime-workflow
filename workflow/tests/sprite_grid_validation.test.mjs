import {test} from 'node:test';
import assert from 'node:assert/strict';
import {invalidSpriteGrid,invalidSpriteGridCount,invalidSpriteFrameRange,spriteFrameIssue,spriteFrameFieldIssues} from '../../gui/spriteGridValidation.mjs';

test('분할 행과 열은 양의 정수이며 셀과 전체 프레임 제한을 지킨다',()=>{
 for(const value of ['',null,0,1.5,129])assert.equal(invalidSpriteGridCount(value),true);
 for(const value of [1,'4',128])assert.equal(invalidSpriteGridCount(value),false);
 assert.equal(invalidSpriteGrid('16','8',{width:16,height:8}),false);
 assert.equal(invalidSpriteGrid('17','8',{width:17,height:8}),true);
 assert.equal(invalidSpriteGrid('5','2',{width:4,height:2}),true);
 assert.equal(invalidSpriteGrid('4','2',null),true);
});


test('GIF 범위는 1부터 전체 프레임까지의 순서 있는 정수다',()=>{
 for(const pair of [['',8],[1,''],[0,8],[1,9],[5,4],[1.5,8]])assert.equal(invalidSpriteFrameRange(...pair,8),true);
 for(const pair of [[1,8],['4','4']])assert.equal(invalidSpriteFrameRange(...pair,8),false);
 assert.equal(invalidSpriteFrameRange(1,1,0),true);
});


test('프레임 크롭과 앵커는 서버가 허용하는 형식과 범위를 따른다',()=>{
 const frame={x:0,y:0,width:10,height:20,anchorX:5,anchorY:19};
 assert.equal(spriteFrameIssue(frame),'');
 for(const changed of [{width:0},{x:1.5},{anchorX:10},{anchorY:-1},{height:''}])assert.ok(spriteFrameIssue({...frame,...changed}));
});


test('크기 오류는 관련 없는 좌표를 표시하지 않고 유효한 크기에서 앵커 범위를 검사한다',()=>{
 const row={x:0,y:0,width:10,height:20,anchorX:5,anchorY:19};
 assert.deepEqual(Object.keys(spriteFrameFieldIssues({...row,width:0})),['width']);
 assert.deepEqual(Object.keys(spriteFrameFieldIssues({...row,width:5})),['anchorX']);
 assert.deepEqual(Object.keys(spriteFrameFieldIssues({...row,x:1.5,anchorY:20})),['x','anchorY']);
});
