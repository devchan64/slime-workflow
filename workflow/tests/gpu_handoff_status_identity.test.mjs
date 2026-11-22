import test from 'node:test';
import assert from 'node:assert/strict';
import {validateGpuHandoffStatus} from '../../gui/validateGpuHandoffStatus.mjs';

test('handoff status must belong to the requested session, service and ID',()=>{
  const record={id:'request-id',session_id:'session-id',service:'flux-image',state:'approved'};
  assert.equal(validateGpuHandoffStatus(record,'session-id','request-id','flux-image'),record);
  for(const altered of [{...record,id:'other'},{...record,session_id:'other'},{...record,service:'kimodo'},{}])
    assert.throws(()=>validateGpuHandoffStatus(altered,'session-id','request-id','flux-image'));
  assert.equal(validateGpuHandoffStatus({state:'not_found',request_id:'request-id'},'session-id','request-id','flux-image').state,'not_found');
  assert.throws(()=>validateGpuHandoffStatus({state:'not_found',request_id:'other'},'session-id','request-id','flux-image'));
});
