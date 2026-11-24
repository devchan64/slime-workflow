import test from 'node:test';
import assert from 'node:assert/strict';
import {validGeneratorHistoryPage} from '../../gui/generatorHistoryPage.mjs';

test('이력 페이지의 경계, 다음 위치, 중복과 스냅샷을 확인한다',()=>{
  const snapshot='a'.repeat(64), row=id=>({id,recorded_status:'completed'});
  const page={records:[row('one'),row('two')],total:3,offset:0,next_offset:2,snapshot};
  assert.equal(validGeneratorHistoryPage(page,0,2),true);
  assert.equal(validGeneratorHistoryPage({...page,next_offset:3},0,2),false);
  assert.equal(validGeneratorHistoryPage({...page,next_offset:null},0,2),false);
  assert.equal(validGeneratorHistoryPage({...page,records:[row('one'),row('one')]},0,2),false);
  assert.equal(validGeneratorHistoryPage({...page,total:1},0,2),false);
  assert.equal(validGeneratorHistoryPage(page,0,1),false);
  assert.equal(validGeneratorHistoryPage(page,0,2,'b'.repeat(64)),false);
  assert.equal(validGeneratorHistoryPage({records:[row('three')],total:3,offset:2,next_offset:null,snapshot},2,2,snapshot),true);
  assert.equal(validGeneratorHistoryPage({records:[],total:0,offset:0,next_offset:null,snapshot},0,2),true);
  assert.equal(validGeneratorHistoryPage({records:[],total:1,offset:0,next_offset:0,snapshot},0,2),false);
});
