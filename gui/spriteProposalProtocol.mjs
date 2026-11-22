export async function spriteProposalRequestId(session,job){
  if(!/^[a-f0-9]{32}$/.test(session || '') || !/^\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2}-[a-f0-9]{8}$/.test(job || '') || !globalThis.crypto?.subtle)throw new Error('대화·작업 식별자를 확인할 수 없습니다.');
  const bytes=await crypto.subtle.digest('SHA-256',new TextEncoder().encode(`${session}:${job}:sprite`));
  return 'chat_'+Array.from(new Uint8Array(bytes),value=>value.toString(16).padStart(2,'0')).join('');
}
export async function verifySpriteMembership(command,session,job,snapshot,offset){
  if(!/^[a-f0-9]{64}$/.test(snapshot || '') || !Number.isInteger(offset) || offset<0)throw new Error('대화 이력 정보를 확인할 수 없습니다.');
  const page=await command('hermes-agent','hermes-session-view',{session_id:session,offset,limit:6,snapshot});
  if(page.id!==session || page.offset!==offset || page.snapshot!==snapshot || !Array.isArray(page.messages) || page.messages.filter(message=>message.job_id===job && message.session_job_unique===true && message.job?.status?.status==='completed' && !message.job?.final_response_truncated && typeof message.job?.final_response==='string' && message.job.final_response.includes('HERMES_SPRITE_PROPOSAL')).length!==1)throw new Error('대화 이력이 변경되었거나 제안 작업을 확인할 수 없습니다.');
}
export function validateSpriteReceipt(receipt,id,path){
  if(receipt?.state==='not_found')return null;
  if(!receipt || receipt.request_id!==id || (receipt.path && receipt.path!==path))throw new Error('스프라이트 접수 대상이 제안과 일치하지 않습니다.');
  return receipt;
}
export async function prepareSpriteProposal(command,session,job,snapshot,offset){
  const id=await spriteProposalRequestId(session,job);
  await verifySpriteMembership(command,session,job,snapshot,offset);
  const response=await command('hermes-agent','hermes-sprite-proposal',{id:job});
  if(response.job_id!==job || typeof response.proposal?.path!=='string')throw new Error('스프라이트 제안을 확인할 수 없습니다.');
  const draft=response.proposal;
  const receipt=validateSpriteReceipt(await command('hermes-agent','hermes-sprite-receipt',{request_id:id}),id,draft.path);
  if(receipt)return {receipt};
  const preview=await command('hermes-agent','hermes-sprite-preview',{draft});
  if(preview.path!==draft.path || !Array.isArray(preview.changed_anchors) || !Array.isArray(preview.frame_layout) || !Array.isArray(preview.clips) || !/^[a-f0-9]{64}$/.test(preview.token || '') || !/^[a-f0-9]{64}$/.test(preview.review_sha256 || '') || !/^[a-f0-9]{64}$/.test(preview.output_sha256 || '') || typeof preview.preview_image!=='string' || preview.preview_image.length>12000000 || !/^[A-Za-z0-9+/]+={0,2}$/.test(preview.preview_image))throw new Error('스프라이트 검토 결과를 확인할 수 없습니다.');
  return {review:{id,draft,preview,snapshot,offset}};
}
export async function verifySpriteBeforeSave(command,session,job,review){
  await verifySpriteMembership(command,session,job,review.snapshot,review.offset);
  const latest=await command('hermes-agent','hermes-sprite-proposal',{id:job});
  if(latest.job_id!==job || JSON.stringify(latest.proposal)!==JSON.stringify(review.draft))throw new Error('검토한 스프라이트 제안이 변경되었습니다.');
}
