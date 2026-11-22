import test from 'node:test';
import assert from 'node:assert/strict';
import {restoreSpriteAnchors} from '../../gui/spriteAnchorRestore.mjs';

test('anchor restoration requires the same animation, image and frame crop',()=>{
  const rect={x:0,y:0,width:10,height:20};
  const original={imageSha256:'a'.repeat(64),animation:{animationId:'test.rest',version:'v1',frames:[{frameId:'down_left.0',rect}]}};
  const doc={coordinateMode:'anchor',source:{animationId:'test.rest',animationVersion:'v1',sheets:[{image:'sheet.png',sha256:'a'.repeat(64)}]},frames:[{frameId:'down_left.0',rect,image:'sheet.png',anchor:{x:5,y:18}}]};
  assert.deepEqual(restoreSpriteAnchors(doc,original).rows,[{...rect,anchorX:5,anchorY:18}]);
  assert.throws(()=>restoreSpriteAnchors(doc,{...original,imageSha256:'b'.repeat(64)}),/변경/);
  assert.throws(()=>restoreSpriteAnchors({...doc,source:{...doc.source,animationId:'other'}},original),/일치/);
  assert.throws(()=>restoreSpriteAnchors({...doc,frames:[{...doc.frames[0],rect:{...rect,x:1}}]},original),/변경/);
  const foot={...doc,coordinateMode:'foot-centers',frames:[{...doc.frames[0],points:[{x:2,y:17},{x:6,y:19}]}]};
  assert.deepEqual(restoreSpriteAnchors(foot,original).feet[0],foot.frames[0].points);
  const endpoint={...foot,coordinateMode:'endpoints',frames:[{...foot.frames[0],points:[{x:1,y:16},{x:3,y:18},{x:5,y:18},{x:7,y:20}]}]};
  assert.deepEqual(restoreSpriteAnchors(endpoint,original).feet[0],[{x:2,y:17},{x:6,y:19}]);
});
