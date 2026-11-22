export async function fieldProposalRequestId(session,job){
  if(!/^[a-f0-9]{32}$/.test(session || '') || !/^\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2}-[a-f0-9]{8}$/.test(job || '') || !globalThis.crypto?.subtle)throw new Error('대화·작업 식별자를 확인할 수 없습니다.');
  const bytes=await crypto.subtle.digest('SHA-256',new TextEncoder().encode(`${session}:${job}:field`));
  return 'chat_'+Array.from(new Uint8Array(bytes),value=>value.toString(16).padStart(2,'0')).join('');
}
export function validateFieldReceipt(receipt,id,map){
  if(receipt?.state==='not_found')return null;
  if(!receipt || receipt.request_id!==id || receipt.map!==map)throw new Error('야외 맵 접수 대상이 제안과 일치하지 않습니다.');
  return receipt;
}
export async function verifyFieldMembership(command,session,job,snapshot,offset){
  if(!/^[a-f0-9]{64}$/.test(snapshot || '') || !Number.isInteger(offset) || offset<0)throw new Error('대화 이력 정보를 확인할 수 없습니다.');
  const page=await command('hermes-agent','hermes-session-view',{session_id:session,offset,limit:6,snapshot});
  if(page.id!==session || page.offset!==offset || page.snapshot!==snapshot || !Array.isArray(page.messages) || page.messages.filter(m=>m.job_id===job && m.session_job_unique===true && m.job?.status?.status==='completed' && !m.job?.final_response_truncated && typeof m.job?.final_response==='string' && m.job.final_response.includes('HERMES_FIELD_PROPOSAL')).length!==1)throw new Error('대화 이력이 변경되었거나 제안 작업을 확인할 수 없습니다.');
}
export async function prepareFieldProposal(command,session,job,snapshot,offset){
  const id=await fieldProposalRequestId(session,job);
  await verifyFieldMembership(command,session,job,snapshot,offset);
  const response=await command('hermes-agent','hermes-field-proposal',{id:job});
  const proposal=response.proposal;
  if(response.job_id!==job || typeof proposal?.map!=='string' || !Array.isArray(proposal.cells))throw new Error('야외 맵 제안을 확인할 수 없습니다.');
  const receipt=validateFieldReceipt(await command('hermes-agent','hermes-field-receipt',{request_id:id}),id,proposal.map);
  if(receipt)return {receipt};
  const source=await command('hermes-agent','hermes-field-load',{map:proposal.map});
  if(source.map!==proposal.map || source.revision!==proposal.revision)throw new Error('야외 맵 원본 또는 리비전이 변경되었습니다.');
  const draft={map:proposal.map,revision:proposal.revision,cells:proposal.cells,objects:[]};
  const preview=await command('hermes-agent','hermes-field-preview',{draft});
  if(!/^[a-f0-9]{64}$/.test(preview.token || '') || ![true,false,null].includes(preview.save_available))throw new Error('야외 맵 검토 결과를 확인할 수 없습니다.');
  return {review:{id,draft,proposal,source,preview,snapshot,offset}};
}
export async function verifyFieldBeforeSave(command,session,job,review){
  await verifyFieldMembership(command,session,job,review.snapshot,review.offset);
  const latest=await command('hermes-agent','hermes-field-proposal',{id:job});
  if(latest.job_id!==job || JSON.stringify(latest.proposal)!==JSON.stringify(review.proposal))throw new Error('검토한 야외 맵 제안이 변경되었습니다.');
}
export function fieldBlockReason(preview){
  if(preview.save_available===true)return '';
  if(preview.save_block_reason==='database')return 'DB 모드의 신규 저장은 중단되었습니다. 원본과 등록부 동기화를 확인하세요.';
  if(preview.save_block_reason==='interrupted')return '이전 야외 맵 저장이 중단되었습니다. 백업과 원본 상태를 확인하세요.';
  return '저장 차단 사유를 확인할 수 없습니다. 원 서비스의 상태를 확인하세요.';
}
