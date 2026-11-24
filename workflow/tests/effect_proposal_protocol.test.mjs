import test from 'node:test';
import assert from 'node:assert/strict';
import {webcrypto} from 'node:crypto';
import {effectProposalRequestId,prepareEffectProposal,verifyEffectBeforeSave} from '../../gui/effectProposalProtocol.mjs';
import {readBuildingSessionReceipts} from '../../gui/buildingProposalProtocol.mjs';
if(!globalThis.crypto)globalThis.crypto=webcrypto;
const session='a'.repeat(32),job='2026-11-18_00-00-00-12345678',snapshot='b'.repeat(64),draft={id:'fire',revision:'c'.repeat(64),target:[0,0,1,1],alpha:.7,frames:[[0,0,1,1]]};
const page={id:session,offset:0,snapshot,next_offset:null,messages:[{job_id:job,session_job_unique:true,job:{status:{status:'completed'},final_response:'HERMES_EFFECT_PROPOSAL'}}]};
test('review checks session and proposal without saving',async()=>{
 let changed=false;const calls=[];
 const command=async(_service,name)=>{calls.push(name);if(name==='hermes-session-view')return page;if(name==='hermes-effect-proposal')return {job_id:job,proposal:changed?{...draft,alpha:.8}:draft};if(name==='hermes-effect-receipt')return {state:'not_found'};if(name==='hermes-effect-preview')return {id:draft.id,revision:draft.revision,before:{frames:[]},after:{frames:[]},token:'d'.repeat(64)};throw Error(name);};
 const {review}=await prepareEffectProposal(command,session,job,snapshot,0);assert.ok(!calls.includes('hermes-effect-save'));await verifyEffectBeforeSave(command,session,job,review);changed=true;await assert.rejects(verifyEffectBeforeSave(command,session,job,review),/변경/);
});
test('history distinguishes legacy receipts and mismatched targets',async()=>{
 const id=await effectProposalRequestId(session,job);const receipt={state:'completed',request_id:id,saved:true};
 const command=async(_service,name)=>{if(name==='hermes-session-view')return page;if(name==='hermes-effect-proposal')return {job_id:job,proposal:draft};if(name==='hermes-effect-receipt')return receipt;throw Error(name);};
 assert.match((await readBuildingSessionReceipts(command,session)).rows[0][1],/대상 미확인/);
 receipt.effect_id='water';assert.match((await readBuildingSessionReceipts(command,session)).rows[0][1],/조회 불가/);
 receipt.effect_id='fire';receipt.state='unknown';assert.match((await readBuildingSessionReceipts(command,session)).rows[0][1],/접수 확인 필요/);
});
