import test from 'node:test';
import assert from 'node:assert/strict';
import {webcrypto} from 'node:crypto';
import {prepareFieldProposal,verifyFieldBeforeSave,fieldBlockReason,fieldProposalRequestId} from '../../gui/fieldProposalProtocol.mjs';
import {readBuildingSessionReceipts} from '../../gui/buildingProposalProtocol.mjs';
if(!globalThis.crypto)globalThis.crypto=webcrypto;
const session='a'.repeat(32),job='2026-11-18_00-00-00-12345678',snapshot='b'.repeat(64);
const proposal={map:'sample',revision:'revision',cells:[{column:0,row:0,tile:'a',height:1,blocked:false}]};
const source={map:'sample',revision:'revision',tiles:{rows:['b']},terrain:{elevations:[[2]],blocked:[[1]]}};
const page={id:session,offset:0,snapshot,messages:[{job_id:job,session_job_unique:true,job:{status:{status:'completed'},final_response:'HERMES_FIELD_PROPOSAL'}}]};
test('field review checks current revision and never saves during preview',async()=>{
 let changed=false;const calls=[];
 const command=async(_,name)=>{calls.push(name);if(name==='hermes-session-view')return page;if(name==='hermes-field-proposal')return {job_id:job,proposal:changed?{...proposal,revision:'new'}:proposal};if(name==='hermes-field-receipt')return {state:'not_found'};if(name==='hermes-field-load')return source;if(name==='hermes-field-preview')return {token:'c'.repeat(64),save_available:false,save_block_reason:'database'};throw Error(name);};
 const {review}=await prepareFieldProposal(command,session,job,snapshot,0);assert.match(fieldBlockReason(review.preview),/DB 모드/);assert.ok(!calls.includes('hermes-field-save'));
 await verifyFieldBeforeSave(command,session,job,review);changed=true;await assert.rejects(verifyFieldBeforeSave(command,session,job,review),/변경/);
 assert.match(fieldBlockReason({save_available:false,save_block_reason:'interrupted'}),/중단/);assert.match(fieldBlockReason({save_available:null}),/사유를 확인할 수 없습니다/);
});
test('field history verifies receipt map',async()=>{
 const receipt={state:'completed',request_id:await fieldProposalRequestId(session,job),map:'other',saved:true};
 const command=async(_,name)=>name==='hermes-session-view'?page:name==='hermes-field-proposal'?{job_id:job,proposal}:receipt;
 assert.match((await readBuildingSessionReceipts(command,session)).rows[0][1],/조회 불가/);receipt.map='sample';assert.match((await readBuildingSessionReceipts(command,session)).rows[0][1],/야외 맵 저장 기록/);
});
