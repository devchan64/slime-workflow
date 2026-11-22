export async function effectProposalRequestId(session,job){
  if(!/^[a-f0-9]{32}$/.test(session || '') || !/^\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2}-[a-f0-9]{8}$/.test(job || '') || !globalThis.crypto?.subtle)throw new Error('대화·작업 식별자를 확인할 수 없습니다.');
  const bytes=await crypto.subtle.digest('SHA-256',new TextEncoder().encode(`${session}:${job}:effect`));
  return 'chat_'+Array.from(new Uint8Array(bytes),value=>value.toString(16).padStart(2,'0')).join('');
}
export async function verifyEffectMembership(command,session,job,snapshot,offset){
  if(!/^[a-f0-9]{64}$/.test(snapshot || '') || !Number.isInteger(offset) || offset<0)throw new Error('대화 이력 정보를 확인할 수 없습니다.');
  const page=await command('hermes-agent','hermes-session-view',{session_id:session,offset,limit:6,snapshot});
  if(page.id!==session || page.offset!==offset || page.snapshot!==snapshot || !Array.isArray(page.messages) || page.messages.filter(message=>message.job_id===job && message.session_job_unique===true && message.job?.status?.status==='completed' && !message.job?.final_response_truncated && typeof message.job?.final_response==='string' && message.job.final_response.includes('HERMES_EFFECT_PROPOSAL')).length!==1)throw new Error('대화 이력이 변경되었거나 제안 작업을 확인할 수 없습니다.');
}
export function validateEffectReceipt(receipt,id,effectId){
  if(receipt?.state==='not_found')return null;
  if(!receipt || receipt.request_id!==id || (receipt.effect_id && receipt.effect_id!==effectId))throw new Error('이펙트 접수 대상이 제안과 일치하지 않습니다.');
  return receipt;
}
export async function prepareEffectProposal(command,session,job,snapshot,offset){
  const id=await effectProposalRequestId(session,job);
  await verifyEffectMembership(command,session,job,snapshot,offset);
  const response=await command('hermes-agent','hermes-effect-proposal',{id:job});
  if(response.job_id!==job || typeof response.proposal?.id!=='string')throw new Error('이펙트 제안을 확인할 수 없습니다.');
  const draft=response.proposal;
  const receipt=validateEffectReceipt(await command('hermes-agent','hermes-effect-receipt',{request_id:id}),id,draft.id);
  if(receipt)return {receipt};
  const preview=await command('hermes-agent','hermes-effect-preview',{draft});
  if(preview.id!==draft.id || preview.revision!==draft.revision || !preview.before || !preview.after || !Array.isArray(preview.before.frames) || !Array.isArray(preview.after.frames) || !/^[a-f0-9]{64}$/.test(preview.token || ''))throw new Error('이펙트 검토 결과를 확인할 수 없습니다.');
  return {review:{id,draft,preview,snapshot,offset}};
}
export async function verifyEffectBeforeSave(command,session,job,review){
  await verifyEffectMembership(command,session,job,review.snapshot,review.offset);
  const latest=await command('hermes-agent','hermes-effect-proposal',{id:job});
  if(latest.job_id!==job || JSON.stringify(latest.proposal)!==JSON.stringify(review.draft))throw new Error('검토한 이펙트 제안이 변경되었습니다.');
}
