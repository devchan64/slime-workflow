import {test} from 'node:test';
import assert from 'node:assert/strict';
import editSpriteFrames from '../../gui/editSpriteFrames.mjs';

test('일괄 편집은 기존 프레임의 빈 입력을 0으로 바꾸지 않는다',()=>{
 const rows=[[0,0,10,10,5,5],[10,0,'',10,5,5]];
 const [result,message]=editSpriteFrames(rows,'지정 프레임','1','앵커',0,0,0,0,3,3);
 assert.equal(result,rows);
 assert.equal(rows[1][2],'');
 assert.match(message,/빈 입력/);
 const [fixed,success]=editSpriteFrames([[0,0,10,10,5,5],[10,0,10,10,5,5]],'지정 프레임','1','앵커',0,0,0,0,3,3);
 assert.deepEqual(fixed.data[0],[0,0,10,10,3,3]);
 assert.match(success,/1개 프레임/);
});
