import test from 'node:test';
import assert from 'node:assert/strict';
import {webcrypto} from 'node:crypto';
import {prepareSpriteProposal,verifySpriteBeforeSave} from '../../gui/spriteProposalProtocol.mjs';
if(!globalThis.crypto)globalThis.crypto=webcrypto;
const session='a'.repeat(32),job='2026-01-01_00-00-00-abcdef12',snapshot='b'.repeat(64);
const draft={path:'assets/sprite.png',snapshot:'c'.repeat(64),columns:2,anchors:[{frame_id:'one',x:2,y:3}]};
const page={id:session,offset:0,snapshot,messages:[{job_id:job,session_job_unique:true,job:{status:{status:'completed'},final_response:'HERMES_SPRITE_PROPOSAL'}}]};
const preview={path:draft.path,changed_anchors:[],frame_layout:[],clips:[],token:'d'.repeat(64),review_sha256:'e'.repeat(64),output_sha256:'f'.repeat(64),preview_image:'aGVsbG8='};
test('sprite preview does not save and approval checks session and proposal',async()=>{
  let changed=false;const calls=[];
  const command=async(_service,name)=>{calls.push(name);if(name==='hermes-session-view')return page;if(name==='hermes-sprite-proposal')return {job_id:job,proposal:changed?{...draft,columns:3}:draft};if(name==='hermes-sprite-receipt')return {state:'not_found'};if(name==='hermes-sprite-preview')return preview;throw Error(name);};
  const {review}=await prepareSpriteProposal(command,session,job,snapshot,0);
  assert.equal(review.draft,draft);assert.ok(!calls.includes('hermes-sprite-save'));
  await verifySpriteBeforeSave(command,session,job,review);changed=true;
  await assert.rejects(verifySpriteBeforeSave(command,session,job,review),/변경/);
});
test('sprite receipt must identify the intended target',async()=>{
  const command=async(_service,name)=>name==='hermes-session-view'?page:name==='hermes-sprite-proposal'?{job_id:job,proposal:draft}:{state:'completed',request_id:'wrong',path:draft.path};
  await assert.rejects(prepareSpriteProposal(command,session,job,snapshot,0),/일치/);
});
