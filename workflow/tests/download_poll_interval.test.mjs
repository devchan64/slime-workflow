import test from 'node:test';
import assert from 'node:assert/strict';
import {downloadPollInterval} from '../../gui/downloadPollInterval.mjs';
import {liveJobStatus} from '../../gui/liveJobStatus.mjs';
test('active downloads refresh quickly and inactive or unknown status refreshes slowly',()=>{
  assert.equal(downloadPollInterval(true),5000);
  for(const value of [false,null,undefined,'running'])assert.equal(downloadPollInterval(value),30000);
});
test('observed completed and failed jobs stop live refresh',()=>{
  assert.equal(liveJobStatus(null),true);
  for(const status of ['queued','running'])assert.equal(liveJobStatus({status}),true);
  for(const status of ['completed','failed','cancelled','paused'])assert.equal(liveJobStatus({status}),false);
});
