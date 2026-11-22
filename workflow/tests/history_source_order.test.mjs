import test from 'node:test';
import assert from 'node:assert/strict';
import {orderHistorySources} from '../../gui/historySourceOrder.mjs';
test('current history sources appear first without losing archived services',()=>{
 const rows=[{service:'old-a',archived:true},{service:'flux-image',archived:false},{service:'old-b',archived:true},{service:'kimodo',archived:false}];
 assert.deepEqual(orderHistorySources(rows).map(row=>row.service),['flux-image','kimodo','old-a','old-b']);
 assert.equal(rows[0].service,'old-a');assert.deepEqual(orderHistorySources([]),[]);
});
