import test from 'node:test';
import assert from 'node:assert/strict';
import {fluxProposalRequestId,classifyFluxProposalReceipt} from '../../gui/fluxProposalReceipt.mjs';

test('a proposal shares a receipt across tabs but separates sessions and services', async () => {
  const session='a'.repeat(32), job='2026-11-22_09-33-14-f9df6f1e';
  const first=await fluxProposalRequestId(session,job,'flux-image');
  assert.equal(first,'flux_136734ccb596e1f95b4384c2f92824da6bd55a8c7209b32b783e0fce549df236');
  assert.match(first,/^flux_[a-f0-9]{64}$/);
  assert.equal(first,await fluxProposalRequestId(session,job,'flux-image'));
  assert.notEqual(first,await fluxProposalRequestId('b'.repeat(32),job,'flux-image'));
  assert.notEqual(first,await fluxProposalRequestId(session,job,'flux-character'));
  await assert.rejects(fluxProposalRequestId(session,'../bad','flux-image'));
});

test('receipt recovery accepts only matching service, request and valid job', () => {
  const request_id='flux_'+ 'a'.repeat(64), service='flux-image', job_id='2026-11-22_09-33-14-f9df6f1e';
  assert.deepEqual(classifyFluxProposalReceipt({request_id,service,state:'accepted',job_id},request_id,service),{state:'accepted',job:job_id});
  assert.deepEqual(classifyFluxProposalReceipt({request_id,service,state:'not_found'},request_id,service),{state:'editing'});
  for(const value of [{request_id,service,state:'unknown'}, {request_id,service,state:'accepted',job_id:'bad'}])
    assert.deepEqual(classifyFluxProposalReceipt(value,request_id,service),{state:'unknown'});
  assert.throws(()=>classifyFluxProposalReceipt({request_id,service:'flux-prop',state:'accepted',job_id},request_id,service));
  assert.throws(()=>classifyFluxProposalReceipt({request_id:'other',service,state:'accepted',job_id},request_id,service));
});

test('an insecure browser receives an actionable error instead of submitting', async () => {
  const descriptor=Object.getOwnPropertyDescriptor(globalThis,'crypto');
  try {
    Object.defineProperty(globalThis,'crypto',{value:{},configurable:true});
    await assert.rejects(fluxProposalRequestId('a'.repeat(32),'2026-11-22_09-33-14-f9df6f1e','flux-image'),/localhost 또는 HTTPS/);
  } finally {
    Object.defineProperty(globalThis,'crypto',descriptor);
  }
});

test('FLUX proposal must belong to the same unchanged session and job',async()=>{
  const {verifyFluxProposal}=await import('../../gui/fluxProposalReceipt.mjs');
  const session='a'.repeat(32),job='2026-11-18_00-00-00-12345678',snapshot='b'.repeat(64);
  const scope={session,job,snapshot,offset:0};
  const proposal={service:'flux-image',prompt:'test',steps:16};
  const page={id:session,offset:0,snapshot,messages:[{job_id:job,session_job_unique:true,job:{status:{status:'completed'},final_response:'HERMES_FLUX_PROPOSAL'}}]};
  let latest=proposal;
  const command=async(_service,name)=>name==='hermes-session-view'?page:{job_id:job,proposal:latest};
  assert.deepEqual(await verifyFluxProposal(command,scope),proposal);
  await verifyFluxProposal(command,scope,proposal);
  latest={...proposal,prompt:'changed'};
  await assert.rejects(verifyFluxProposal(command,scope,proposal),/변경/);
  latest=proposal;page.messages[0].session_job_unique=false;
  await assert.rejects(verifyFluxProposal(command,scope,proposal),/확인할 수 없습니다/);
});


test('rejected receipt is distinct from an uncertain submission',()=>{
  assert.deepEqual(classifyFluxProposalReceipt({request_id:'x',service:'flux-image',state:'rejected'},'x','flux-image'),{state:'rejected'});
});

test('MiniMax proposal identifiers match the gateway receipt contract',async()=>{
  assert.equal(await fluxProposalRequestId('a'.repeat(32),'2026-11-24_10-00-00-12345678','minimax-h3-image'),
    'flux_8ea9de353c6e763076102d659ccdde42cea293e9f92f423142143ae51fdcdedc');
  assert.match(await fluxProposalRequestId('a'.repeat(32),'2026-11-24_10-00-00-12345678','minimax-h3-i2v'),/^flux_[a-f0-9]{64}$/);
});
