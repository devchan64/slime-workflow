import test from 'node:test';
import assert from 'node:assert/strict';
import {verifyKimodoProposal} from '../../gui/kimodoProposalMembership.mjs';

test('Kimodo proposal requires one unchanged completed job in the session',async()=>{
  const session='a'.repeat(32),job='2026-11-18_00-00-00-12345678',snapshot='b'.repeat(64);
  const scope={session,job,snapshot,offset:0},proposal={example_id:'walking'};
  const page={id:session,offset:0,snapshot,messages:[{job_id:job,session_job_unique:true,job:{status:{status:'completed'},final_response:'HERMES_KIMODO_PROPOSAL'}}]};
  let current=proposal;
  const command=async(_service,name)=>name==='hermes-session-view'?page:{job_id:job,proposal:current};
  assert.deepEqual(await verifyKimodoProposal(command,scope),proposal);
  await verifyKimodoProposal(command,scope,proposal);
  current={example_id:'other'};
  await assert.rejects(verifyKimodoProposal(command,scope,proposal),/변경/);
  current=proposal;page.messages[0].session_job_unique=false;
  await assert.rejects(verifyKimodoProposal(command,scope,proposal),/확인할 수 없습니다/);
  page.messages[0].session_job_unique=true;page.snapshot='c'.repeat(64);
  await assert.rejects(verifyKimodoProposal(command,scope,proposal),/확인할 수 없습니다/);
});

test('손상된 Kimodo 제안은 폼에 전달하지 않는다',async()=>{
 const session='a'.repeat(32),job='2026-11-18_00-00-00-12345678',snapshot='b'.repeat(64),scope={session,job,snapshot,offset:0};
 const page={id:session,offset:0,snapshot,messages:[{job_id:job,session_job_unique:true,job:{status:{status:'completed'},final_response:'HERMES_KIMODO_PROPOSAL'}}]};
 for(const proposal of [{},[],{prompt:42,frames:30,steps:2,seed:1},{prompt:'walk',frames:0,steps:2,seed:1},{example_id:''}]){
  const command=async(_service,name)=>name==='hermes-session-view'?page:{job_id:job,proposal};
  await assert.rejects(verifyKimodoProposal(command,scope),/확인할 수 없습니다/);
 }
 const proposal={prompt:'walk',frames:30,steps:2,seed:1};
 assert.deepEqual(await verifyKimodoProposal(async(_service,name)=>name==='hermes-session-view'?page:{job_id:job,proposal},scope),proposal);
});
