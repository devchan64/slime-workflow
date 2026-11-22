import test from 'node:test';
import assert from 'node:assert/strict';
import {latestRequest} from '../../gui/latestRequest.mjs';
import {anchorHistoryRequest,validAnchorHistoryPage} from '../../gui/anchorHistoryPage.mjs';
import {validSourceHistoryPage} from '../../gui/sourceHistoryPage.mjs';

test('new requests and edits invalidate late responses',()=>{
  const requests=latestRequest();
  const first=requests.start();
  assert.equal(requests.isCurrent(first),true);
  const second=requests.start();
  assert.equal(requests.isCurrent(first),false);
  assert.equal(requests.isCurrent(second),true);
  requests.invalidate();
  assert.equal(requests.isCurrent(second),false);
});

test('anchor history pages retain the requested offset and snapshot',()=>{
  const snapshot='a'.repeat(64),payload={offset:1,snapshot};
  const page={records:[{id:'one'}],offset:1,next_offset:2,snapshot};
  assert.equal(validAnchorHistoryPage(page,payload,true),true);
  assert.equal(validAnchorHistoryPage({...page,snapshot:'b'.repeat(64)},payload,true),false);
  assert.equal(validAnchorHistoryPage({...page,offset:0},payload,true),false);
  assert.equal(validAnchorHistoryPage({...page,next_offset:3},payload,true),false);
  assert.equal(validAnchorHistoryPage({...page,records:[],next_offset:1},payload,true),false);
  assert.equal(validAnchorHistoryPage({...page,next_offset:null},payload,true),true);
});

test('anchor history requests retain trimmed filters and pagination snapshot',()=>{
  const first=anchorHistoryRequest(' walk ',' v1 ');
  assert.deepEqual(first,{animation_id:'walk',animation_version:'v1',limit:20});
  assert.deepEqual(anchorHistoryRequest(' walk ',' v1 ',{next_offset:20,snapshot:'a'.repeat(64)}),
    {...first,offset:20,snapshot:'a'.repeat(64)});
});

test('generator history rejects malformed or mismatched pages before rendering',()=>{
  const snapshot='a'.repeat(64);
  const page={service:'flux-image',records:[{id:'job',recorded_status:'completed'}],total:1,offset:0,next_offset:null,snapshot,unavailable_count:0};
  assert.equal(validSourceHistoryPage(page,'flux-image',0),true);
  assert.equal(validSourceHistoryPage({...page,records:null},'flux-image',0),false);
  assert.equal(validSourceHistoryPage({...page,service:'kimodo'},'flux-image',0),false);
  assert.equal(validSourceHistoryPage(page,'flux-image',0,'b'.repeat(64)),false);
  assert.equal(validSourceHistoryPage({...page,next_offset:0},'flux-image',0),false);
});
