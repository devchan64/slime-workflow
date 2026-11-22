import {test} from 'node:test';
import assert from 'node:assert/strict';
import {validSessionListPage} from '../../gui/sessionListPage.mjs';

const row=id=>({id:id.padStart(32,'0'),updated_at:'2026-11-22T00:00:00Z'});
const snapshot='a'.repeat(64);
test('session pages accept search rows without titles and validate snapshot',()=>{
  const page={sessions:[row('1')],offset:0,total:2,next_offset:1,snapshot};
  assert.equal(validSessionListPage(page,{offset:0}),true);
  assert.equal(validSessionListPage({...page,offset:1,next_offset:null},{offset:1,snapshot}),true);
  assert.equal(validSessionListPage(page,{offset:0,snapshot:'b'.repeat(64)}),false);
});
test('session pages reject invalid rows, duplicates and inconsistent pagination',()=>{
  const page={sessions:[row('1')],offset:0,total:1,next_offset:null,snapshot};
  for(const invalid of [
    {...page,sessions:[null]}, {...page,sessions:[row('1'),row('1')],total:2},
    {...page,total:2}, {...page,total:2,next_offset:2}, {...page,offset:1},
  ])assert.equal(validSessionListPage(invalid,{offset:0}),false);
});
