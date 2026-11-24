import {test} from 'node:test';
import assert from 'node:assert/strict';
import {classifyVideoReceipt} from '../../gui/videoDelegationReceipt.mjs';

const id='proposal_123',service='minimax-h3-ref2va',job='2026-11-24_22-38-58-ec4f928e';
test('only a matching absent or accepted receipt permits the corresponding action',()=>{
  assert.equal(classifyVideoReceipt({receipt:{request_id:id,service,state:'not_found'}},id,service).state,'editing');
  assert.deepEqual(classifyVideoReceipt({receipt:{request_id:id,service,state:'accepted',job_id:job}},id,service),{state:'accepted',id,job});
  assert.equal(classifyVideoReceipt({receipt:{request_id:id,service,state:'accepted',job_id:'bad'}},id,service).state,'unknown');
  assert.equal(classifyVideoReceipt({receipt:{request_id:id,service,state:'unknown'}},id,service).state,'unknown');
  assert.throws(()=>classifyVideoReceipt({receipt:{request_id:'wrong',service,state:'not_found'}},id,service));
  assert.throws(()=>classifyVideoReceipt({receipt:{request_id:id,service:'wrong',state:'not_found'}},id,service));
});
