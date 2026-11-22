import test from 'node:test';
import assert from 'node:assert/strict';
import {readCaptureProposal} from '../../gui/captureProposal.mjs';

test('capture proposal checks session and map registration without executing capture',async()=>{
  const session='a'.repeat(32),job='2026-11-18_00-00-00-12345678',snapshot='b'.repeat(64),calls=[];
  const scope={session,job,snapshot,offset:0};
  const page={id:session,offset:0,snapshot,messages:[{job_id:job,session_job_unique:true,job:{status:{status:'completed'},final_response:'HERMES_CAPTURE_PROPOSAL'}}]};
  const response={job_id:job,proposal:{service:'map-review',settings:{map:'test-map',edges:false}},map_registration:{status:'registered',map:'test-map'}};
  const command=async(_service,name)=>{calls.push(name);return name==='hermes-session-view'?page:response;};
  assert.equal((await readCaptureProposal(command,scope)).registration.status,'registered');
  assert.deepEqual(calls,['hermes-session-view','hermes-capture-proposal']);
  response.map_registration.map='other';await assert.rejects(readCaptureProposal(command,scope),/일치하지 않습니다/);
  response.map_registration.map='test-map';page.messages[0].session_job_unique=false;
  await assert.rejects(readCaptureProposal(command,scope),/확인할 수 없습니다/);
});
