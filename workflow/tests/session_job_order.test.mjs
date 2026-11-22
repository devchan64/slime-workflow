import {test} from 'node:test';
import assert from 'node:assert/strict';
import {newestSessionJobs,parseSessionTime} from '../../gui/sessionJobOrder.mjs';

test('orders mixed jobs by creation time, including requests without a job ID',()=>{
  const rows=[
    {step:{request_id:'old',created_at:'2026-11-21T10:00:00Z',source_job_id:'2026-11-21_19-00-00-aaaaaaaa'}},
    {step:{request_id:'new',created_at:'2026-11-21T20:00:00+09:00'}},
    {step:{request_id:'missing'}},
    {step:{request_id:'invalid',created_at:'invalid'}},
  ];
  assert.deepEqual(newestSessionJobs(rows).map(row=>row.step.request_id),['new','old','missing','invalid']);
  assert.equal(rows[0].step.request_id,'old');
});

test('SQLite timestamps represent UTC independent of the browser timezone',()=>{
  assert.equal(parseSessionTime('2026-11-21 09:52:16'),Date.parse('2026-11-21T09:52:16Z'));
  const rows=[{step:{created_at:'2026-11-21T09:31:07+00:00'}},{step:{created_at:'2026-11-21 09:52:16'}}];
  assert.equal(newestSessionJobs(rows)[0],rows[1]);
});
