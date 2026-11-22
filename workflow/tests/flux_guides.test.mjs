import test from 'node:test';
import assert from 'node:assert/strict';
import {filterFluxGuides,addFluxRolePrompt} from '../../gui/fluxGuides.mjs';

test('guide search combines words across labels and metadata',()=>{
  const guides=[{id:'building-01',label:'4x4 남쪽 2층',roof:'flat',entrance:'south'}, {id:'building-02',label:'2x2 북쪽 1층',roof:'gable',entrance:'north'}];
  assert.deepEqual(filterFluxGuides(guides,'4x4 남쪽').map(item=>item.id),['building-01']);
  assert.deepEqual(filterFluxGuides(guides,'BUILDING flat').map(item=>item.id),['building-01']);
  assert.equal(filterFluxGuides(guides,'없는 검색어').length,0);
  assert.equal(filterFluxGuides(guides,'').length,2);
});

test('reference role guidance is added once',()=>{
  assert.equal(addFluxRolePrompt('portrait','reference role'),'portrait reference role');
  assert.equal(addFluxRolePrompt('portrait reference role','reference role'),'portrait reference role');
});
