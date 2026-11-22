import test from 'node:test';
import assert from 'node:assert/strict';
import {linkedSpriteSheet,findLinkedSprite} from '../../gui/spriteSourceLink.mjs';
test('links preserve valid source and select only one exact animation match',()=>{
  assert.deepEqual(linkedSpriteSheet('?sprite_path=rest.png&sprite_source=baseline'),{path:'rest.png',source:'baseline'});
  assert.ok(linkedSpriteSheet('?sprite_path=rest.png&sprite_source=outside').error);
  assert.deepEqual(linkedSpriteSheet('?action=asset%3Acharacter.rest'),{source:'assets',animation:'character.rest'});
  assert.ok(linkedSpriteSheet('?action=asset%3A').error);
  const rows=[{path:'rest.png',animationIds:['character.rest']},{path:'other.png',animationIds:['character.rest.extra']}];
  assert.equal(findLinkedSprite(rows,'character.rest'),'rest.png');
  assert.equal(findLinkedSprite([...rows,{path:'another.png',animationIds:['character.rest']}],'character.rest'),null);
  assert.equal(findLinkedSprite([null,{path:'bad',animationIds:'character.rest'}],'character.rest'),null);
});
