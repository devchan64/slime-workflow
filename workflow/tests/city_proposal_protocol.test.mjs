import test from 'node:test';
import assert from 'node:assert/strict';
import {webcrypto} from 'node:crypto';
import {applyCityChanges,prepareCityProposal,cityProposalRequestId} from '../../gui/cityProposalProtocol.mjs';
import {readBuildingSessionReceipts} from '../../gui/buildingProposalProtocol.mjs';
if(!globalThis.crypto)globalThis.crypto=webcrypto;
const session='a'.repeat(32),job='2026-11-18_00-00-00-12345678',snapshot='b'.repeat(64);
const proposal={map:'town',generation:5,revision:2,changes:[{path:['data','buildings',0,'name'],before:'old',after:'new'}]};
const source={map:'town',generation:5,revision:2,document:{data:{buildings:[{name:'old'}]}}};
const page={id:session,offset:0,snapshot,next_offset:null,messages:[{job_id:job,session_job_unique:true,job:{status:{status:'completed'},final_response:'HERMES_CITY_PROPOSAL'}}]};
test('city review checks old values and preserves the loaded document',()=>{
 assert.equal(applyCityChanges(source,proposal).document.data.buildings[0].name,'new');assert.equal(source.document.data.buildings[0].name,'old');
 assert.throws(()=>applyCityChanges({...source,revision:3},proposal),/변경/);
 assert.throws(()=>applyCityChanges(source,{...proposal,changes:[{...proposal.changes[0],before:'different'}]}),/변경/);
 assert.throws(()=>applyCityChanges(source,{...proposal,changes:[{path:['data','__proto__','x'],before:1,after:2}]}),/경로/);
});
test('city review is read only and validates session and receipt target',async()=>{
 const calls=[];let receipt={state:'not_found'};
 const command=async(_,name)=>{calls.push(name);if(name==='hermes-session-view')return page;if(name==='hermes-city-proposal')return {job_id:job,proposal};if(name==='hermes-city-receipt')return receipt;if(name==='hermes-city-load')return source;if(name==='hermes-city-preview')return {cityId:'town',token:'c'.repeat(64),save_available:false};throw Error(name);};
 const result=await prepareCityProposal(command,session,job,snapshot,0);assert.equal(result.preview.save_available,false);assert.ok(!calls.includes('hermes-city-save'));
 receipt={state:'completed',saved:true,request_id:await cityProposalRequestId(session,job),map:'other'};
 await assert.rejects(prepareCityProposal(command,session,job,snapshot,0),/일치/);
 assert.match((await readBuildingSessionReceipts(command,session)).rows[0][1],/조회 불가/);
 receipt.map='town';assert.match((await readBuildingSessionReceipts(command,session)).rows[0][1],/도시 DB 저장 기록/);
});
