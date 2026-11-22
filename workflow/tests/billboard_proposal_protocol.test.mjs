import test from 'node:test';
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {billboardProposalRequestId,prepareBillboardProposal,validateBillboardReceipt,verifyBillboardBeforeSave,verifyBillboardMembership} from '../../gui/billboardProposalProtocol.mjs';
import {readBuildingSessionReceipts} from '../../gui/buildingProposalProtocol.mjs';

test('billboard receipt ID retains existing session and job binding',async()=>{
  const session='a'.repeat(32),job='2026-11-18_00-00-00-12345678';
  assert.equal(await billboardProposalRequestId(session,job),'chat_'+createHash('sha256').update(`${session}:${job}:billboard`).digest('hex'));
  await assert.rejects(billboardProposalRequestId(session,'../bad'));
});
test('billboard receipt targets must match the complete proposal',()=>{
  const changes=[{texture:'tree-a'},{texture:'tree-b'}],id='chat_1';
  assert.equal(validateBillboardReceipt({state:'not_found'},id,changes),null);
  assert.ok(validateBillboardReceipt({request_id:id,state:'completed',saved:true},id,changes));
  assert.ok(validateBillboardReceipt({request_id:id,state:'completed',saved:true,textures:['tree-b','tree-a']},id,changes));
  assert.throws(()=>validateBillboardReceipt({request_id:id,state:'completed',saved:true,textures:['tree-a']},id,changes));
});
test('billboard proposal must remain in the same completed session page',async()=>{
  const snapshot='a'.repeat(64),session='session',job='job';
  const page={id:session,offset:0,snapshot,messages:[{job_id:job,session_job_unique:true,job:{status:{status:'completed'},final_response:'HERMES_BILLBOARD_PROPOSAL'}}]};
  await verifyBillboardMembership(async()=>page,session,job,snapshot,0);
  await assert.rejects(verifyBillboardMembership(async()=>({...page,messages:[{...page.messages[0],session_job_unique:false}]}),session,job,snapshot,0));
});

test('session history attributes billboard receipts only to matching targets',async()=>{
  const session='a'.repeat(32),job='2026-11-18_00-00-00-12345678',snapshot='a'.repeat(64);
  const id=await billboardProposalRequestId(session,job);
  const view={id:session,offset:0,snapshot,messages:[{job_id:job,session_job_unique:true,job:{status:{status:'completed'},final_response:'HERMES_BILLBOARD_PROPOSAL'}}]};
  let textures=['tree-a'];
  const command=async(_,name)=>name==='hermes-session-view'?view:name==='hermes-billboard-proposal'?
    {job_id:job,proposal:{texture:'tree-a'}}:{request_id:id,state:'completed',saved:true,textures};
  assert.match((await readBuildingSessionReceipts(command,session)).rows[0][1],/tree-a/);
  textures=['tree-b'];
  assert.match((await readBuildingSessionReceipts(command,session)).rows[0][1],/조회 불가/);
});

test('session history retains sprite identity and handles legacy or mismatched receipts',async()=>{
  const session='a'.repeat(32),job='2026-11-18_00-00-00-12345678',snapshot='a'.repeat(64);
  const id='chat_'+createHash('sha256').update(`${session}:${job}:sprite`).digest('hex');
  const view={id:session,offset:0,snapshot,messages:[{job_id:job,session_job_unique:true,job:{status:{status:'completed'},final_response:'HERMES_SPRITE_PROPOSAL'}}]};
  let receipt={request_id:id,state:'completed',saved:true};
  const command=async(_,name)=>name==='hermes-session-view'?view:name==='hermes-sprite-proposal'?{job_id:job,proposal:{path:'assets/sprites/test.png'}}:receipt;
  assert.match((await readBuildingSessionReceipts(command,session)).rows[0][1],/대상 미확인/);
  receipt={...receipt,path:'assets/sprites/other.png'};
  assert.match((await readBuildingSessionReceipts(command,session)).rows[0][1],/조회 불가/);
  receipt={...receipt,path:'assets/sprites/test.png',state:'unknown'};
  assert.match((await readBuildingSessionReceipts(command,session)).rows[0][1],/접수 확인 필요/);
});

test('preview never saves and a changed proposal cannot be approved',async()=>{
  const session='a'.repeat(32),job='2026-11-18_00-00-00-12345678',snapshot='b'.repeat(64);
  const proposal={texture:'tree-a',expected:{displayHeight:5},values:{displayHeight:10}};
  const page={id:session,offset:0,snapshot,messages:[{job_id:job,session_job_unique:true,job:{status:{status:'completed'},final_response:'HERMES_BILLBOARD_PROPOSAL'}}]};
  const preview={changes:[{texture:'tree-a',before:{displayHeight:5},after:{displayHeight:10}}],maps:[],map_warnings:[],token:'c'.repeat(64),review_sha256:'d'.repeat(64)};
  const calls=[];let latest=proposal,source={texture:'tree-a',revision:'rev',properties:{displayHeight:5}};
  const command=async(_,name)=>{calls.push(name);if(name==='hermes-session-view')return page;if(name==='hermes-billboard-proposal')return {job_id:job,proposal:latest};if(name==='hermes-billboard-receipt')return {state:'not_found'};if(name==='hermes-billboard-load')return source;if(name==='hermes-billboard-preview')return preview;throw Error(name);};
  const {review}=await prepareBillboardProposal(command,session,job,snapshot,0);
  await verifyBillboardBeforeSave(command,session,job,review);
  latest={...proposal,values:{displayHeight:11}};
  await assert.rejects(verifyBillboardBeforeSave(command,session,job,review),/변경/);
  latest=proposal;source={...source,properties:{displayHeight:6}};
  await assert.rejects(prepareBillboardProposal(command,session,job,snapshot,0),/현재 속성/);
  assert.equal(calls.includes('hermes-billboard-save'),false);
});

test('initial billboard settings preserve default fields in the reviewed draft',async()=>{
  const session='a'.repeat(32),job='2026-11-18_00-00-00-12345678',snapshot='b'.repeat(64);
  const proposal={texture:'tree-a',expected:{displayHeight:128},values:{displayHeight:130}};
  const page={id:session,offset:0,snapshot,messages:[{job_id:job,session_job_unique:true,job:{status:{status:'completed'},final_response:'HERMES_BILLBOARD_PROPOSAL'}}]};
  const preview={changes:[{texture:'tree-a',before:{displayHeight:128},after:{displayHeight:130}}],maps:[],map_warnings:[],token:'c'.repeat(64),review_sha256:'d'.repeat(64)};
  const command=async(_,name,payload)=>{
    if(name==='hermes-session-view')return page;
    if(name==='hermes-billboard-proposal')return {job_id:job,proposal};
    if(name==='hermes-billboard-receipt')return {state:'not_found'};
    if(name==='hermes-billboard-load')return {texture:'tree-a',revision:'rev',initial:true,properties:{displayHeight:128,anchorX:0,anchorY:0}};
    if(name==='hermes-billboard-preview'){assert.deepEqual(payload.draft.changes[0].values,{displayHeight:130,anchorX:0,anchorY:0});return preview;}
    throw Error(name);
  };
  await prepareBillboardProposal(command,session,job,snapshot,0);
});
