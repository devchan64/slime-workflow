import test from 'node:test';
import assert from 'node:assert/strict';
import {buildingProposalRequestId,buildingReceiptStatus,prepareBuildingProposal,readBuildingSessionReceipts,verifyBuildingProposalBeforeSave,verifyBuildingProposalMembership} from '../../gui/buildingProposalProtocol.mjs';
import {createHash} from 'node:crypto';

test('building receipt ID preserves the existing session and job binding',async()=>{
  const session='a'.repeat(32),job='2026-11-18_00-00-00-12345678';
  const expected='chat_'+createHash('sha256').update(`${session}:${job}:building`).digest('hex');
  assert.equal(await buildingProposalRequestId(session,job),expected);
  assert.notEqual(await buildingProposalRequestId('b'.repeat(32),job),expected);
  await assert.rejects(buildingProposalRequestId(session,'../bad'));
});

test('building history does not attribute a receipt to a different target',()=>{
  const id='chat_123',texture='town-test-v1';
  assert.equal(buildingReceiptStatus({state:'not_found'},id,texture),null);
  assert.match(buildingReceiptStatus({request_id:id,state:'completed',saved:true},id,texture),/대상 미확인/);
  assert.match(buildingReceiptStatus({request_id:id,state:'completed',saved:true,texture,ledger_status_at_save:'pending'},id,texture),/원장 반영 대기/);
  assert.equal(buildingReceiptStatus({request_id:id,state:'unknown',texture},id,texture),'접수 확인 필요');
  assert.throws(()=>buildingReceiptStatus({request_id:id,state:'completed',saved:true,texture:'town-other-v1'},id,texture));
});

test('session history checks the target and revalidates the snapshot',async()=>{
  const session='a'.repeat(32),job='2026-11-18_00-00-00-12345678',snapshot='a'.repeat(64);
  const id=await buildingProposalRequestId(session,job);
  const view={id:session,offset:0,snapshot,next_offset:null,messages:[{job_id:job,session_job_unique:true,job:{status:{status:'completed'},final_response:'HERMES_BUILDING_PROPOSAL'}}]};
  let returned={request_id:id,state:'completed',saved:true,texture:'town-test-v1'},views=0;
  const command=async(_service,name)=>{
    if(name==='hermes-session-view'){views++;return view;}
    if(name==='hermes-building-proposal')return {job_id:job,proposal:{texture:'town-test-v1'}};
    if(name==='hermes-building-receipt')return returned;
    throw Error(name);
  };
  const result=await readBuildingSessionReceipts(command,session);
  assert.equal(views,2);assert.match(result.rows[0][1],/town-test-v1/);assert.equal(result.rows[0][2],'GPU 작업 아님');
  returned={...returned,texture:'town-other-v1'};
  assert.equal((await readBuildingSessionReceipts(command,session)).rows[0][1],'제안 또는 접수 조회 불가');
  let count=0;
  await assert.rejects(readBuildingSessionReceipts(async(service,name,payload)=>{
    if(name==='hermes-session-view' && ++count===2)return {...view,snapshot:'b'.repeat(64)};
    return command(service,name,payload);
  },session));
});
test('session receipt pages reject malformed or changed next positions',async()=>{
  const session='a'.repeat(32),snapshot='b'.repeat(64),page={id:session,offset:0,snapshot,messages:[{}],next_offset:1};
  for(const invalid of [{...page,next_offset:0},{...page,next_offset:2},{...page,next_offset:'1'},{...page,next_offset:undefined},{...page,messages:Array(7).fill({}),next_offset:7},{...page,messages:[null]}]){
    await assert.rejects(readBuildingSessionReceipts(async()=>invalid,session),/페이지를 확인/);
  }
  let calls=0;await assert.rejects(readBuildingSessionReceipts(async()=>++calls===1?page:{...page,next_offset:null},session),/이력이 변경/);
  await assert.rejects(readBuildingSessionReceipts(async()=>page,session,-1),/페이지를 확인/);
  const result=await readBuildingSessionReceipts(async()=>page,session);assert.equal(result.page.next_offset,1);
});

test('building review rechecks the current source and never saves during preview',async()=>{
  const session='a'.repeat(32),job='2026-11-18_00-00-00-12345678',snapshot='b'.repeat(64);
  const calls=[],draft={texture:'town-test-v1'},preview={texture:draft.texture,before:{anchorX:0.5},after:{anchorX:0.6},maps:['test-city'],review_sha256:'c'.repeat(64)};
  let changed=false;
  const command=async(_service,name)=>{
    calls.push(name);
    if(name==='hermes-session-view')return {id:session,offset:0,snapshot,next_offset:null,messages:[{job_id:job,session_job_unique:true,job:{status:{status:'completed'},final_response:'HERMES_BUILDING_PROPOSAL'}}]};
    if(name==='hermes-building-proposal')return {job_id:job,proposal:draft};
    if(name==='hermes-building-receipt')return {state:'not_found'};
    if(name==='hermes-building-preview'){if(changed)throw Error('건물 원본 변경');return preview;}
    throw Error('unexpected save');
  };
  assert.equal((await prepareBuildingProposal(command,session,job,snapshot,0)).review.preview,preview);
  await verifyBuildingProposalBeforeSave(command,session,job,{snapshot,offset:0,draft});
  await assert.rejects(verifyBuildingProposalBeforeSave(command,session,job,{snapshot,offset:0,draft:{texture:'other'}}),/변경/);
  changed=true;
  await assert.rejects(prepareBuildingProposal(command,session,job,snapshot,0),/원본 변경/);
  assert.equal(calls.includes('hermes-building-save'),false);
});

test('building review only accepts a unique job in the same session snapshot',async()=>{
  const snapshot='a'.repeat(64), session='session', job='job';
  const page={id:session,snapshot,offset:6,messages:[{job_id:job,session_job_unique:true,job:{status:{status:'completed'},final_response:'HERMES_BUILDING_PROPOSAL'}}]};
  await verifyBuildingProposalMembership(async(service,command,payload)=>{
    assert.equal(service,'hermes-agent');assert.equal(command,'hermes-session-view');
    assert.deepEqual(payload,{session_id:session,offset:6,limit:6,snapshot});return page;
  },session,job,snapshot,6);
  for(const invalid of [{...page,id:'other'},{...page,snapshot:'b'.repeat(64)},
                        {...page,messages:[{job_id:job,session_job_unique:false}]},
                        {...page,messages:[...page.messages,...page.messages]}])
    await assert.rejects(verifyBuildingProposalMembership(async()=>invalid,session,job,snapshot,6));
});
