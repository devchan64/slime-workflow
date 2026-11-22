export async function billboardProposalRequestId(session,job){
  if(!/^[a-f0-9]{32}$/.test(session || '') || !/^\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2}-[a-f0-9]{8}$/.test(job || '') || !globalThis.crypto?.subtle)throw new Error('대화·작업 식별자 또는 안전한 접수 기능을 확인하세요.');
  const bytes=await crypto.subtle.digest('SHA-256',new TextEncoder().encode(`${session}:${job}:billboard`));
  return 'chat_'+Array.from(new Uint8Array(bytes),value=>value.toString(16).padStart(2,'0')).join('');
}
export async function verifyBillboardMembership(command,session,job,snapshot,offset){
  if(!/^[a-f0-9]{64}$/.test(snapshot || '') || !Number.isInteger(offset) || offset<0)throw new Error('대화 이력 정보를 확인할 수 없습니다.');
  const page=await command('hermes-agent','hermes-session-view',{session_id:session,offset,limit:6,snapshot});
  if(page.id!==session || page.offset!==offset || page.snapshot!==snapshot || !Array.isArray(page.messages) ||
    page.messages.filter(message=>message.job_id===job && message.session_job_unique===true && message.job?.status?.status==='completed' && !message.job?.final_response_truncated && message.job?.final_response?.includes('HERMES_BILLBOARD_PROPOSAL')).length!==1)
    throw new Error('대화 이력이 변경되었거나 제안 작업을 확인할 수 없습니다.');
}
export function validateBillboardReceipt(receipt,id,changes){
  if(receipt?.state==='not_found')return null;
  if(!receipt || receipt.request_id!==id)throw new Error('빌보드 접수 ID가 일치하지 않습니다.');
  if(receipt.textures){
    if(!Array.isArray(receipt.textures) || JSON.stringify([...receipt.textures].sort())!==JSON.stringify(changes.map(change=>change.texture).sort()))throw new Error('빌보드 접수 대상이 제안과 일치하지 않습니다.');
  }
  return receipt;
}

export async function prepareBillboardProposal(command,session,job,snapshot,offset){
  const id=await billboardProposalRequestId(session,job);
  await verifyBillboardMembership(command,session,job,snapshot,offset);
  const response=await command('hermes-agent','hermes-billboard-proposal',{id:job});
  const proposal=response.proposal;
  if(response.job_id!==job || typeof proposal?.texture!=='string' || !proposal.expected || !proposal.values)throw new Error('빌보드 제안을 확인할 수 없습니다.');
  const changes=[{texture:proposal.texture}];
  const receipt=validateBillboardReceipt(await command('hermes-agent','hermes-billboard-receipt',{request_id:id}),id,changes);
  if(receipt)return {receipt};
  const source=await command('hermes-agent','hermes-billboard-load',{texture:proposal.texture});
  if(source.texture!==proposal.texture || typeof source.revision!=='string' || !source.properties ||
    Object.entries(proposal.expected).some(([key,value])=>source.properties[key]!==value))throw new Error('빌보드 현재 속성이 변경되었습니다. 다시 조회하세요.');
  const values=source.initial ? {...source.properties,...proposal.values} : proposal.values;
  const draft={revision:source.revision,changes:[{texture:proposal.texture,values}]};
  const preview=await command('hermes-agent','hermes-billboard-preview',{draft});
  if(!Array.isArray(preview.changes) || preview.changes.length!==draft.changes.length || preview.changes.some((change,index)=>change.texture!==draft.changes[index].texture || !change.before || !change.after) || !Array.isArray(preview.maps) || !Array.isArray(preview.map_warnings) || !/^[a-f0-9]{64}$/.test(preview.token || '') || !/^[a-f0-9]{64}$/.test(preview.review_sha256 || ''))throw new Error('빌보드 검토 결과를 확인할 수 없습니다.');
  return {review:{id,draft,proposal,preview,snapshot,offset}};
}
export async function verifyBillboardBeforeSave(command,session,job,review){
  await verifyBillboardMembership(command,session,job,review.snapshot,review.offset);
  const latest=await command('hermes-agent','hermes-billboard-proposal',{id:job});
  if(latest.job_id!==job || JSON.stringify(latest.proposal)!==JSON.stringify(review.proposal))throw new Error('검토한 빌보드 제안이 변경되었습니다.');
}
